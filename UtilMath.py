def get_max_mod_media(media_list, count):
    max_mod = 0
    max_index = 0
    for i in range(count + 1, media_list.__len__()):
        if int(media_list[i]['mod']) > max_mod:
            max_mod = int(media_list[i]['mod'])
            max_index = i
    return max_index


def get_max_group_media(media_list, count):
    if media_list.__len__() < 0 or media_list.__len__() < count:
        return None
    res = []
    for i in range(count):
        max_index = get_max_mod_media(media_list, count)
        if int(media_list[max_index]['mod']) > int(media_list[i]['mod']):
            temp = media_list[i]
            media_list[i] = media_list[max_index]
            media_list[max_index] = temp
    for i in range(count):
        res.append(media_list[i])
    return res
