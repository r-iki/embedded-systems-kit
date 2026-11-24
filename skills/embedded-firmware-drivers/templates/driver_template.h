/**
 * @file driver_template.h
 * @brief HAL-agnostic C99/C11 embedded device driver template.
 *
 * Replace `dev_` / `DEV_` prefixes with your actual sensor or IC name.
 */

#ifndef DEV_DRIVER_H
#define DEV_DRIVER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Typed driver status codes (negative values indicate errors). */
typedef enum {
    DEV_OK = 0,
    DEV_ERR_INVALID_ARG = -1,
    DEV_ERR_NOT_INIT = -2,
    DEV_ERR_BUS = -3,
    DEV_ERR_TIMEOUT = -4,
    DEV_ERR_BAD_ID = -5,
    DEV_ERR_CRC = -6,
} dev_status_t;

/**
 * @brief Platform-injected bus and timing callbacks.
 *
 * All callbacks return 0 on success, non-zero on failure.
 */
typedef struct {
    int32_t (*write_reg)(void *ctx, uint8_t dev_addr, uint8_t reg, const uint8_t *data, size_t len, uint32_t timeout_ms);
    int32_t (*read_reg)(void *ctx, uint8_t dev_addr, uint8_t reg, uint8_t *data, size_t len, uint32_t timeout_ms);
    void (*delay_ms)(void *ctx, uint32_t ms);
    void *ctx;
} dev_hal_t;

/** Immutable hardware configuration. */
typedef struct {
    uint8_t addr_7bit;
    uint32_t timeout_ms;
} dev_config_t;

/** Caller-allocated device handle (zero dynamic allocation). */
typedef struct {
    dev_hal_t hal;
    dev_config_t cfg;
    bool initialized;
} dev_handle_t;

/** Sample measurement payload. */
typedef struct {
    int32_t value_milli;
    uint16_t raw_counts;
} dev_sample_t;

dev_status_t dev_init(dev_handle_t *dev, const dev_hal_t *hal, const dev_config_t *cfg);
dev_status_t dev_deinit(dev_handle_t *dev);
dev_status_t dev_read_sample(dev_handle_t *dev, dev_sample_t *out);

#ifdef __cplusplus
}
#endif

#endif /* DEV_DRIVER_H */
