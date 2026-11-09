#include "graphics/common/WordPredict.h"

#include <cstring>

namespace WordPredict
{
namespace
{
#include "predict_wordlist.inc"

char asciiLower(char c)
{
    return (c >= 'A' && c <= 'Z') ? (char)(c + ('a' - 'A')) : c;
}

bool startsWithIgnoreCase(const char *word, const char *prefix, uint8_t prefixLen)
{
    for (uint8_t i = 0; i < prefixLen; i++) {
        if (asciiLower(word[i]) != prefix[i])
            return false;
    }
    return true;
}

} // namespace

uint8_t predict(const char *prefix, char out[][kMaxWordLen], uint8_t maxCount)
{
    if (!prefix || !out || maxCount == 0)
        return 0;

    uint8_t prefixLen = strlen(prefix);
    if (prefixLen == 0 || prefixLen >= kMaxWordLen - 1)
        return 0;

    char lowerPrefix[kMaxWordLen];
    bool allUpper = true;
    for (uint8_t i = 0; i < prefixLen; i++) {
        lowerPrefix[i] = asciiLower(prefix[i]);
        if (lowerPrefix[i] == prefix[i]) // character was not an uppercase letter
            allUpper = false;
    }
    bool firstUpper = (prefix[0] >= 'A' && prefix[0] <= 'Z') && !allUpper;

    uint8_t count = 0;
    const char *p = kPredictWordList;
    while (*p && count < maxCount) {
        uint8_t wordLen = 0;
        while (p[wordLen] && p[wordLen] != '\n')
            wordLen++;
        if (wordLen > prefixLen && wordLen < kMaxWordLen && startsWithIgnoreCase(p, lowerPrefix, prefixLen)) {
            for (uint8_t i = 0; i < wordLen; i++)
                out[count][i] = allUpper ? (char)(p[i] - ('a' - 'A')) : (firstUpper && i == 0 ? (char)(p[i] - ('a' - 'A')) : p[i]);
            out[count][wordLen] = '\0';
            count++;
        }
        p += wordLen;
        if (*p == '\n')
            p++;
    }
    return count;
}

} // namespace WordPredict
