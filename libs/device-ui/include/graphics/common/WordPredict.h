#pragma once

#include <cstdint>

/**
 * @brief Prefix based English word prediction for the virtual keyboard.
 * Words are matched case-insensitively against an embedded frequency ordered
 * word list stored in flash. Candidate casing follows the typed prefix.
 */
namespace WordPredict
{
inline constexpr uint8_t kMaxCandidates = 3;
inline constexpr uint8_t kMaxWordLen = 16; // incl. terminating zero

/**
 * @brief Find up to maxCount words starting with prefix, frequency ordered.
 *
 * @param prefix current partial word (letters only, any casing)
 * @param out candidate buffer filled with zero terminated words
 * @param maxCount capacity of out
 * @return number of candidates filled into out
 */
uint8_t predict(const char *prefix, char out[][kMaxWordLen], uint8_t maxCount);

} // namespace WordPredict
