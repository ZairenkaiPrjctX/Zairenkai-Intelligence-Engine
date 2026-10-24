// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 ZairenkaiPrjctX contributors
//
// zie-run: the on-device runner of Zairenkai Local AI. Loads a GGUF model with llama.cpp's core
// library, reads a prompt from a file, and generates at most N tokens greedily under a GBNF
// grammar, printing only the generated text. It links llama and ggml alone (no llama.cpp common,
// no HTTP client): the binary contains no networking code (scripts/build-android.sh checks its
// imported symbols), so inference cannot reach the network, whatever the model emits.
//
// usage: zie-run -m MODEL.gguf -g GRAMMAR.gbnf -f PROMPT.txt [-n MAX_TOKENS] [-c CTX] [-t THREADS] [-v]
// exit:  0 ok, 2 usage, 3 model, 4 grammar, 5 prompt, 6 decode
#include "llama.h"

#include <clocale>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#ifndef ZIE_LLAMA_TAG
#define ZIE_LLAMA_TAG "unknown"
#endif

namespace {

constexpr size_t MAX_FILE = 64 * 1024;
bool verbose = false;

void quiet_log(ggml_log_level level, const char * text, void *) {
    if (verbose || level == GGML_LOG_LEVEL_ERROR) fputs(text, stderr);
}

bool read_file(const char * path, std::string & out) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return false;
    std::ostringstream ss;
    ss << f.rdbuf();
    out = ss.str();
    return out.size() <= MAX_FILE;
}

bool to_int(const char * s, int lo, int hi, int & out) {
    char * end = nullptr;
    long v = strtol(s, &end, 10);
    if (end == s || *end != '\0' || v < lo || v > hi) return false;
    out = static_cast<int>(v);
    return true;
}

void set_tokens(llama_batch_ext * batch, const llama_token * tokens, int32_t n, llama_pos pos0) {
    llama_batch_ext_clear(batch);
    for (int32_t i = 0; i < n; ++i) {
        const int32_t idx = llama_batch_ext_add_token(batch, 0, tokens[i]);
        const llama_pos pos = pos0 + i;
        llama_batch_ext_set_pos(batch, idx, &pos);
    }
    llama_batch_ext_set_output_logits(batch, n - 1, true);
}

int usage() {
    fputs("usage: zie-run -m MODEL.gguf -g GRAMMAR.gbnf -f PROMPT.txt [-n MAX_TOKENS] [-c CTX] [-t THREADS] [-v]\n", stderr);
    return 2;
}

}  // namespace

int main(int argc, char ** argv) {
    std::setlocale(LC_NUMERIC, "C");
    const char * model_path = nullptr;
    const char * grammar_path = nullptr;
    const char * prompt_path = nullptr;
    int n_predict = 160, n_ctx = 2048, n_threads = 4;
    for (int i = 1; i < argc; ++i) {
        const char * a = argv[i];
        const bool has = i + 1 < argc;
        if (!strcmp(a, "-v")) verbose = true;
        else if (!strcmp(a, "-m") && has) model_path = argv[++i];
        else if (!strcmp(a, "-g") && has) grammar_path = argv[++i];
        else if (!strcmp(a, "-f") && has) prompt_path = argv[++i];
        else if (!strcmp(a, "-n") && has) { if (!to_int(argv[++i], 1, 1024, n_predict)) return usage(); }
        else if (!strcmp(a, "-c") && has) { if (!to_int(argv[++i], 256, 8192, n_ctx)) return usage(); }
        else if (!strcmp(a, "-t") && has) { if (!to_int(argv[++i], 1, 16, n_threads)) return usage(); }
        else if (!strcmp(a, "--version")) { printf("zie-run 1 (llama.cpp %s)\n", ZIE_LLAMA_TAG); return 0; }
        else return usage();
    }
    if (!model_path || !grammar_path || !prompt_path) return usage();

    std::string grammar, prompt;
    if (!read_file(grammar_path, grammar)) { fputs("zie-run: cannot read the grammar\n", stderr); return 4; }
    if (!read_file(prompt_path, prompt) || prompt.empty()) { fputs("zie-run: cannot read the prompt\n", stderr); return 5; }

    llama_log_set(quiet_log, nullptr);
    llama_backend_init();

    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = 0;  // CPU only: the same path on every device
    llama_model * model = llama_model_load_from_file(model_path, mp);
    if (!model) { fputs("zie-run: cannot load the model\n", stderr); return 3; }
    const llama_vocab * vocab = llama_model_get_vocab(model);

    const int n_prompt = -llama_tokenize(vocab, prompt.c_str(), prompt.size(), nullptr, 0, true, true);
    if (n_prompt <= 0 || n_prompt + n_predict > n_ctx) { fputs("zie-run: the prompt does not fit the context\n", stderr); return 5; }
    std::vector<llama_token> tokens(n_prompt);
    if (llama_tokenize(vocab, prompt.c_str(), prompt.size(), tokens.data(), tokens.size(), true, true) < 0) {
        fputs("zie-run: cannot tokenize the prompt\n", stderr);
        return 5;
    }

    llama_context_params cp = llama_context_default_params();
    cp.n_ctx = n_ctx;
    cp.n_batch = n_prompt;
    cp.n_threads = n_threads;
    cp.n_threads_batch = n_threads;
    llama_context * ctx = llama_init_from_model(model, cp);
    if (!ctx) { fputs("zie-run: cannot create the context\n", stderr); return 3; }

    llama_sampler * smpl = llama_sampler_chain_init(llama_sampler_chain_default_params());
    llama_sampler * g = llama_sampler_init_grammar(vocab, grammar.c_str(), "root");
    if (!g) { fputs("zie-run: the grammar does not parse\n", stderr); return 4; }
    llama_sampler_chain_add(smpl, g);
    llama_sampler_chain_add(smpl, llama_sampler_init_greedy());

    llama_batch_ext * batch = llama_batch_ext_init(ctx);
    set_tokens(batch, tokens.data(), n_prompt, 0);
    int n_tokens = n_prompt;
    std::string out;
    for (int n_pos = 0; n_pos + n_tokens < n_prompt + n_predict;) {
        if (llama_process(ctx, LLAMA_PROCESS_TYPE_DECODE, batch)) { fputs("zie-run: decode failed\n", stderr); return 6; }
        n_pos += n_tokens;
        llama_token id = llama_sampler_sample(smpl, ctx, -1);
        if (llama_vocab_is_eog(vocab, id)) break;
        char buf[256];
        const int n = llama_token_to_piece(vocab, id, buf, sizeof(buf), 0, false);
        if (n < 0) { fputs("zie-run: cannot decode a token\n", stderr); return 6; }
        out.append(buf, n);
        if (out.size() > MAX_FILE) break;
        set_tokens(batch, &id, 1, n_pos);
        n_tokens = 1;
    }
    fwrite(out.data(), 1, out.size(), stdout);
    fputc('\n', stdout);

    llama_batch_ext_free(batch);
    llama_sampler_free(smpl);
    llama_free(ctx);
    llama_model_free(model);
    llama_backend_free();
    return 0;
}
