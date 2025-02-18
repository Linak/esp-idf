/*
 * SPDX-FileCopyrightText: 2016-2021 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Apache-2.0
 */


#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <sys/param.h>
#include "esp_attr.h"
#include "esp_cpu.h"
#include "soc/wdev_reg.h"
#include "esp_private/esp_clk.h"

#if defined CONFIG_IDF_TARGET_ESP32C6
#include "hal/lp_timer_hal.h"
#endif

#if defined CONFIG_IDF_TARGET_ESP32S3
#define APB_CYCLE_WAIT_NUM (1778) /* If APB clock is 80 MHz, maximum sampling frequency is around 45 KHz*/
                                  /* 45 KHz reading frequency is the maximum we have tested so far on S3 */
#elif defined CONFIG_IDF_TARGET_ESP32C6
#define APB_CYCLE_WAIT_NUM (160 * 5) /* We want to have a maximum sampling frequency below 50KHz for
                                      * 32-bit samples. But on ESP32C6, we only read one byte at a time,
                                      * hence, the wait time is 4 times lower. The current value translates
                                      * to a sampling frequency of 50 KHz for reading 32 bit samples,
                                      * plus additional overhead for the calculation, making it slower. */
#elif defined CONFIG_IDF_TARGET_ESP32H2
#define APB_CYCLE_WAIT_NUM (160 * 3) /* Same reasoning as for ESP32C6, but the CPU frequency on ESP32H2 is
                                      * 96MHz instead of 160 MHz */
#else
#define APB_CYCLE_WAIT_NUM (16)
#endif

#if defined CONFIG_IDF_TARGET_ESP32H2

// TODO: temporary definition until IDF-6270 is implemented
#include "soc/lp_timer_reg.h"

static uint32_t IRAM_ATTR lp_timer_hal_get_cycle_count(void)
{
    REG_SET_BIT(LP_TIMER_UPDATE_REG, LP_TIMER_MAIN_TIMER_UPDATE);

    uint32_t lo = REG_GET_FIELD(LP_TIMER_MAIN_BUF0_LOW_REG, LP_TIMER_MAIN_TIMER_BUF0_LOW);
    return lo;
}
#endif

uint32_t IRAM_ATTR esp_random(void)
{
    /* The PRNG which implements WDEV_RANDOM register gets 2 bits
     * of extra entropy from a hardware randomness source every APB clock cycle
     * (provided WiFi or BT are enabled). To make sure entropy is not drained
     * faster than it is added, this function needs to wait for at least 16 APB
     * clock cycles after reading previous word. This implementation may actually
     * wait a bit longer due to extra time spent in arithmetic and branch statements.
     *
     * As a (probably unncessary) precaution to avoid returning the
     * RNG state as-is, the result is XORed with additional
     * WDEV_RND_REG reads while waiting.
     */

    /* This code does not run in a critical section, so CPU frequency switch may
     * happens while this code runs (this will not happen in the current
     * implementation, but possible in the future). However if that happens,
     * the number of cycles spent on frequency switching will certainly be more
     * than the number of cycles we need to wait here.
     */
    uint32_t cpu_to_apb_freq_ratio = esp_clk_cpu_freq() / esp_clk_apb_freq();

    static uint32_t last_ccount = 0;
    uint32_t ccount;
    uint32_t result = 0;
#if (defined CONFIG_IDF_TARGET_ESP32C6 || defined CONFIG_IDF_TARGET_ESP32H2)
    for (size_t i = 0; i < sizeof(result); i++) {
        do {
            ccount = esp_cpu_get_cycle_count();
            result ^= REG_READ(WDEV_RND_REG);
        } while (ccount - last_ccount < cpu_to_apb_freq_ratio * APB_CYCLE_WAIT_NUM);
        uint32_t current_rtc_timer_counter = (lp_timer_hal_get_cycle_count() & 0xFF);
        result ^= ((result ^ current_rtc_timer_counter) & 0xFF) << (i * 8);
    }
#else
    do {
        ccount = esp_cpu_get_cycle_count();
        result ^= REG_READ(WDEV_RND_REG);
    } while (ccount - last_ccount < cpu_to_apb_freq_ratio * APB_CYCLE_WAIT_NUM);
#endif
    last_ccount = ccount;
    return result ^ REG_READ(WDEV_RND_REG);
}

void esp_fill_random(void *buf, size_t len)
{
    assert(buf != NULL);
    uint8_t *buf_bytes = (uint8_t *)buf;
    while (len > 0) {
        uint32_t word = esp_random();
        uint32_t to_copy = MIN(sizeof(word), len);
        memcpy(buf_bytes, &word, to_copy);
        buf_bytes += to_copy;
        len -= to_copy;
    }
}
