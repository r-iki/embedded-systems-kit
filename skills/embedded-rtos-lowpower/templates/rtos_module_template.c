/**
 * @file rtos_module_template.c
 * @brief FreeRTOS static-allocation worker/gatekeeper module template.
 *
 * Requires configSUPPORT_STATIC_ALLOCATION == 1 in FreeRTOSConfig.h.
 * Note: StackType_t count is words on upstream/STM32 FreeRTOS, bytes on ESP-IDF.
 */

#include <stdbool.h>
#include <stdint.h>

#include "FreeRTOS.h"
#include "queue.h"
#include "task.h"

#define MOD_TASK_STACK_DEPTH  (512U)
#define MOD_TASK_PRIORITY     (tskIDLE_PRIORITY + 2U)
#define MOD_QUEUE_LENGTH      (8U)

typedef enum {
    MOD_CMD_SAMPLE = 0,
    MOD_CMD_FLUSH,
} mod_cmd_type_t;

typedef struct {
    mod_cmd_type_t type;
    uint32_t arg;
} mod_msg_t;

static StaticTask_t s_task_tcb;
static StackType_t s_task_stack[MOD_TASK_STACK_DEPTH];
static TaskHandle_t s_task_handle = NULL;

static StaticQueue_t s_queue_cb;
static uint8_t s_queue_storage[MOD_QUEUE_LENGTH * sizeof(mod_msg_t)];
static QueueHandle_t s_queue_handle = NULL;

static void mod_process_msg(const mod_msg_t *msg) {
    switch (msg->type) {
        case MOD_CMD_SAMPLE:
            /* Perform bounded peripheral I/O owned exclusively by this task. */
            break;
        case MOD_CMD_FLUSH:
            break;
        default:
            break;
    }
}

static void mod_task_entry(void *arg) {
    (void)arg;
    mod_msg_t msg;

    for (;;) {
        /* Block cleanly on queue; never spin-wait. */
        if (xQueueReceive(s_queue_handle, &msg, pdMS_TO_TICKS(1000U)) == pdTRUE) {
            mod_process_msg(&msg);
        } else {
            /* Periodic housekeeping / watchdog heartbeat on timeout. */
        }
    }
}

bool mod_start(void) {
    if (s_task_handle != NULL) {
        return true;
    }

    s_queue_handle = xQueueCreateStatic(
        MOD_QUEUE_LENGTH,
        sizeof(mod_msg_t),
        s_queue_storage,
        &s_queue_cb
    );
    if (s_queue_handle == NULL) {
        return false;
    }

    s_task_handle = xTaskCreateStatic(
        mod_task_entry,
        "mod_worker",
        MOD_TASK_STACK_DEPTH,
        NULL,
        MOD_TASK_PRIORITY,
        s_task_stack,
        &s_task_tcb
    );
    return (s_task_handle != NULL);
}

bool mod_post_msg(const mod_msg_t *msg, uint32_t timeout_ms) {
    if ((s_queue_handle == NULL) || (msg == NULL)) {
        return false;
    }
    return (xQueueSend(s_queue_handle, msg, pdMS_TO_TICKS(timeout_ms)) == pdTRUE);
}

bool mod_post_msg_from_isr(const mod_msg_t *msg, BaseType_t *higher_prio_woken) {
    if ((s_queue_handle == NULL) || (msg == NULL)) {
        return false;
    }
    return (xQueueSendFromISR(s_queue_handle, msg, higher_prio_woken) == pdTRUE);
}
