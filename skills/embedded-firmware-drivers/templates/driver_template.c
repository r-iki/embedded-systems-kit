/**
 * @file driver_template.c
 * @brief HAL-agnostic C99/C11 embedded device driver implementation template.
 */

#include "driver_template.h"

/* TODO: Replace with verified register addresses from the IC datasheet. */
#define DEV_REG_WHO_AM_I   (0x00U)
#define DEV_REG_CTRL       (0x01U)
#define DEV_REG_DATA_MSB   (0x02U)
#define DEV_EXPECTED_ID    (0xA5U)
#define DEV_DEFAULT_TMO_MS (50U)

static dev_status_t dev_read_u8(const dev_handle_t *dev, uint8_t reg, uint8_t *val) {
    int32_t rc = dev->hal.read_reg(dev->hal.ctx, dev->cfg.addr_7bit, reg, val, 1U, dev->cfg.timeout_ms);
    return (rc == 0) ? DEV_OK : DEV_ERR_BUS;
}

static dev_status_t dev_write_u8(const dev_handle_t *dev, uint8_t reg, uint8_t val) {
    int32_t rc = dev->hal.write_reg(dev->hal.ctx, dev->cfg.addr_7bit, reg, &val, 1U, dev->cfg.timeout_ms);
    return (rc == 0) ? DEV_OK : DEV_ERR_BUS;
}

dev_status_t dev_init(dev_handle_t *dev, const dev_hal_t *hal, const dev_config_t *cfg) {
    if ((dev == NULL) || (hal == NULL) || (cfg == NULL)) {
        return DEV_ERR_INVALID_ARG;
    }
    if ((hal->read_reg == NULL) || (hal->write_reg == NULL)) {
        return DEV_ERR_INVALID_ARG;
    }

    dev->hal = *hal;
    dev->cfg = *cfg;
    if (dev->cfg.timeout_ms == 0U) {
        dev->cfg.timeout_ms = DEV_DEFAULT_TMO_MS;
    }
    dev->initialized = false;

    uint8_t who_am_i = 0U;
    dev_status_t st = dev_read_u8(dev, DEV_REG_WHO_AM_I, &who_am_i);
    if (st != DEV_OK) {
        return st;
    }
    if (who_am_i != DEV_EXPECTED_ID) {
        return DEV_ERR_BAD_ID;
    }

    /* Example configuration write; verify bitmasks against datasheet. */
    st = dev_write_u8(dev, DEV_REG_CTRL, 0x01U);
    if (st != DEV_OK) {
        return st;
    }

    if (dev->hal.delay_ms != NULL) {
        dev->hal.delay_ms(dev->hal.ctx, 5U);
    }

    dev->initialized = true;
    return DEV_OK;
}

dev_status_t dev_deinit(dev_handle_t *dev) {
    if (dev == NULL) {
        return DEV_ERR_INVALID_ARG;
    }
    dev->initialized = false;
    return DEV_OK;
}

dev_status_t dev_read_sample(dev_handle_t *dev, dev_sample_t *out) {
    if ((dev == NULL) || (out == NULL)) {
        return DEV_ERR_INVALID_ARG;
    }
    if (!dev->initialized) {
        return DEV_ERR_NOT_INIT;
    }

    uint8_t raw[2] = {0U, 0U};
    int32_t rc = dev->hal.read_reg(dev->hal.ctx, dev->cfg.addr_7bit, DEV_REG_DATA_MSB, raw, sizeof(raw), dev->cfg.timeout_ms);
    if (rc != 0) {
        return DEV_ERR_BUS;
    }

    /* Explicit big-endian unpack (no unaligned/packed struct cast). */
    uint16_t counts = (uint16_t)(((uint16_t)raw[0] << 8U) | (uint16_t)raw[1]);
    out->raw_counts = counts;
    out->value_milli = (int32_t)counts; /* Replace with datasheet scaling formula. */
    return DEV_OK;
}
