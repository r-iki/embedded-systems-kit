/**
 * @file fsm_template.h
 * @brief Deterministic table-driven Finite State Machine (FSM) template in C99/C11.
 */

#ifndef EMBEDDED_FSM_TEMPLATE_H
#define EMBEDDED_FSM_TEMPLATE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    FSM_STATE_INIT = 0,
    FSM_STATE_IDLE,
    FSM_STATE_ACTIVE,
    FSM_STATE_FAULT,
    FSM_STATE_COUNT
} fsm_state_t;

typedef enum {
    FSM_EVT_NONE = 0,
    FSM_EVT_READY,
    FSM_EVT_START,
    FSM_EVT_STOP,
    FSM_EVT_TIMEOUT,
    FSM_EVT_ERROR,
    FSM_EVT_RESET
} fsm_event_t;

typedef struct fsm_ctx fsm_ctx_t;

typedef bool (*fsm_guard_fn)(const fsm_ctx_t *ctx);
typedef void (*fsm_action_fn)(fsm_ctx_t *ctx, fsm_event_t evt);

typedef struct {
    fsm_state_t from;
    fsm_event_t event;
    fsm_guard_fn guard;   /* optional; NULL means always true */
    fsm_action_fn action; /* optional transition action */
    fsm_state_t to;
} fsm_transition_t;

struct fsm_ctx {
    fsm_state_t state;
    uint32_t state_enter_ms;
    const fsm_transition_t *table;
    size_t table_len;
    void (*on_exit)(fsm_ctx_t *ctx, fsm_state_t old_state);
    void (*on_enter)(fsm_ctx_t *ctx, fsm_state_t new_state);
    void *user_data;
};

static inline void fsm_init(
    fsm_ctx_t *ctx,
    fsm_state_t initial_state,
    const fsm_transition_t *table,
    size_t table_len,
    uint32_t now_ms
) {
    if (ctx == NULL) {
        return;
    }
    ctx->state = initial_state;
    ctx->state_enter_ms = now_ms;
    ctx->table = table;
    ctx->table_len = table_len;
    if (ctx->on_enter != NULL) {
        ctx->on_enter(ctx, initial_state);
    }
}

static inline bool fsm_dispatch(fsm_ctx_t *ctx, fsm_event_t evt, uint32_t now_ms) {
    if ((ctx == NULL) || (ctx->table == NULL)) {
        return false;
    }
    for (size_t i = 0U; i < ctx->table_len; ++i) {
        const fsm_transition_t *t = &ctx->table[i];
        if ((t->from == ctx->state) && (t->event == evt)) {
            if ((t->guard != NULL) && !t->guard(ctx)) {
                continue;
            }
            if ((t->to != ctx->state) && (ctx->on_exit != NULL)) {
                ctx->on_exit(ctx, ctx->state);
            }
            if (t->action != NULL) {
                t->action(ctx, evt);
            }
            if (t->to != ctx->state) {
                ctx->state = t->to;
                ctx->state_enter_ms = now_ms;
                if (ctx->on_enter != NULL) {
                    ctx->on_enter(ctx, ctx->state);
                }
            }
            return true;
        }
    }
    return false;
}

#ifdef __cplusplus
}
#endif

#endif /* EMBEDDED_FSM_TEMPLATE_H */
