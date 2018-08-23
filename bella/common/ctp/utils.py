def struct_to_dict(obj):
    """把CTP的回报数据转换成字典"""
    data = {}
    for k, _ in obj._fields_:
        data[k] = getattr(obj, k)
        if isinstance(data[k], bytes):
            data[k] = data[k].decode('gbk', 'ignore')
    return data
