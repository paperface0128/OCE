CHOSUNG = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ',
           'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

CHOSUNG_SET = set(CHOSUNG)

def get_chosung(char: str) -> str:
    code = ord(char)
    if 0xAC00 <= code <= 0xD7A3:
        return CHOSUNG[(code - 0xAC00) // 588]
    # 미완성 한글 자음 (ㄱ~ㅎ 범위)
    if 0x3131 <= code <= 0x314E:
        return char
    return char.lower()

def word_to_chosung(word: str) -> str:
    return ''.join(get_chosung(c) for c in word)

def match_score(query: str, text: str) -> int:
    if not query:
        return 3

    t_lower = text.lower()

    # 완전 포함
    if query.lower() in t_lower:
        return 4

    # 쿼리를 초성으로 변환해서 텍스트 초성과 비교
    q_chosung = word_to_chosung(query)
    t_chosung = word_to_chosung(text)

    # 초성 완전 포함 (ㄴㅁ가지 → 나뭇가지)
    if q_chosung in t_chosung:
        return 3

    # 순서 매치 (ㄴㅁㄱㅈ → 나뭇가지)
    ti = 0
    matched = 0
    for qc in q_chosung:
        while ti < len(t_chosung):
            if t_chosung[ti] == qc:
                matched += 1
                ti += 1
                break
            ti += 1
        else:
            break

    if matched == len(q_chosung):
        return 2

    return 0


# 캐시로 최적화
_filter_cache: dict = {}

def filter_and_sort(query: str, items: list) -> list:
    if not query:
        return items

    # 캐시 확인
    cache_key = (query, id(items))
    if cache_key in _filter_cache:
        return _filter_cache[cache_key]

    scored = []
    for item in items:
        score = match_score(query, item)
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: (-x[0], x[1]))
    result = [item for _, item in scored]

    # 캐시 크기 제한
    if len(_filter_cache) > 200:
        _filter_cache.clear()
    _filter_cache[cache_key] = result
    return result