from pydantic import BaseModel, Field
from typing import Optional

class GlobalSettingsUpdate(BaseModel):
    githubEnabled: bool = True
    githubToken: str = ""
    githubScanCron: str = ""
    ozoneEnabled: bool = True
    ozoneFetchCron: str = ""
    ozoneScanCron: str = ""
    concurrency: int = Field(64, ge=1, le=500)
    timeout: int = Field(2000, ge=200, le=10000)
    configDelay: int = Field(3, ge=0, le=60)
    janitorCron: str = ""
    # zoomeye 配置
    zoomeyeEnabled: bool = True
    zoomeyeFetchCron: str = ""
    zoomeyeScanCron: str = ""
    daydaymapEnabled: bool = True
    daydaymapFetchCron: str = ""
    daydaymapScanCron: str = ""
    hunterEnabled: bool = True
    hunterApiKey: str = ""
    hunterFetchCron: str = ""
    hunterScanCron: str = ""

class TemplateCreateOrUpdate(BaseModel):
    name: str
    region: str
    operator: str
    targetName: str
    targetAddress: str

class ConfigCreateOrUpdate(BaseModel):
    name: str
    templateId: int
    dataSource: str
    searchDepth: Optional[int] = Field(30, ge=1, le=30)
    enabled: Optional[bool] = True
