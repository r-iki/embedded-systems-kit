/**
 * @file ring_buffer.h
 * @brief Lock-free Single-Producer Single-Consumer (SPSC) byte ring buffer.
 *
 * Safe between one ISR producer and one main/task consumer (or vice versa)
 * on MCUs with atomic 32-bit aligned loads/stores (Cortex-M, ESP32, RP2040).
 * Capacity MUST be a power of two.
 */

#ifndef EMBEDDED_RING_BUFFER_H
#define EMBEDDED_RING_BUFFER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint8_t *buf;
    uint32_t mask;          /* capacity - 1 (capacity must be power of two) */
    volatile uint32_t head; /* written only by producer */
    volatile uint32_t tail; /* written only by consumer */
} ring_buf_t;

static inline bool rb_init(ring_buf_t *rb, uint8_t *storage, uint32_t capacity) {
    if ((rb == NULL) || (storage == NULL) || (capacity < 2U) || ((capacity & (capacity - 1U)) != 0U)) {
        return false;
    }
    rb->buf = storage;
    rb->mask = capacity - 1U;
    rb->head = 0U;
    rb->tail = 0U;
    return true;
}

static inline uint32_t rb_count(const ring_buf_t *rb) {
    return (uint32_t)(rb->head - rb->tail);
}

static inline uint32_t rb_capacity(const ring_buf_t *rb) {
    return rb->mask + 1U;
}

static inline bool rb_is_empty(const ring_buf_t *rb) {
    return rb->head == rb->tail;
}

static inline bool rb_is_full(const ring_buf_t *rb) {
    return rb_count(rb) == rb_capacity(rb);
}

static inline bool rb_push(ring_buf_t *rb, uint8_t byte) {
    uint32_t head = rb->head;
    if ((uint32_t)(head - rb->tail) >= rb_capacity(rb)) {
        return false;
    }
    rb->buf[head & rb->mask] = byte;
#if defined(__GNUC__) || defined(__clang__)
    __atomic_store_n(&rb->head, head + 1U, __ATOMIC_RELEASE);
#else
    rb->head = head + 1U;
#endif
    return true;
}

static inline bool rb_pop(ring_buf_t *rb, uint8_t *out_byte) {
    uint32_t tail = rb->tail;
#if defined(__GNUC__) || defined(__clang__)
    uint32_t head = __atomic_load_n(&rb->head, __ATOMIC_ACQUIRE);
#else
    uint32_t head = rb->head;
#endif
    if (head == tail) {
        return false;
    }
    *out_byte = rb->buf[tail & rb->mask];
#if defined(__GNUC__) || defined(__clang__)
    __atomic_store_n(&rb->tail, tail + 1U, __ATOMIC_RELEASE);
#else
    rb->tail = tail + 1U;
#endif
    return true;
}

#ifdef __cplusplus
}
#endif

#endif /* EMBEDDED_RING_BUFFER_H */
