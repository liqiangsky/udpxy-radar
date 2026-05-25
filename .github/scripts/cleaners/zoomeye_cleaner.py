"""ZoomEye 数据清洗器 — 仅提取 host，geoip 由服务端统一处理"""


def clean(data: dict) -> list[dict]:
    matches = data.get("matches", [])
    sources = []
    for item in matches:
        ip = item.get("ip", "")
        portinfo = item.get("portinfo", {})
        port = portinfo.get("port", "")
        if not port:
            port = item.get("port", "")
        if ip and port:
            sources.append({"host": f"{ip}:{port}"})
    return sources
