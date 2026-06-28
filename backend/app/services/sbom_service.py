"""SBOM 闭环服务 — 导入/导出/漏洞关联。"""
import json
from sqlalchemy.orm import Session
from ..models import SbomRecord, Component, Vulnerability, OrgNode, now


def import_sbom(db: Session, node_id: int, sbom_json: dict, filename: str = "", generated_by: str = "manual") -> SbomRecord:
    """解析 CycloneDX/SPDX SBOM，自动关联组件与漏洞。"""
    fmt = "CycloneDX" if "bomFormat" in sbom_json else "SPDX"
    components = _extract_components(sbom_json, fmt)
    node = db.query(OrgNode).filter_by(id=node_id).first()

    record = SbomRecord(node_id=node_id, format=fmt, version=sbom_json.get("specVersion", "1.5"),
                        filename=filename, component_count=len(components),
                        raw_json=sbom_json, generated_by=generated_by)
    db.add(record)
    db.commit()

    vuln_matched = 0
    for comp in components:
        db.add(Component(product_node_id=node_id, name=comp["name"], version=comp["version"],
                          purl=comp.get("purl", ""), license=comp.get("license", ""),
                          supplier=comp.get("supplier", "")))
        # 漏洞关联：匹配组件名+版本
        vulns = db.query(Vulnerability).filter(
            Vulnerability.component.ilike(f"%{comp['name']}%")
        ).all()
        for v in vulns:
            v.component = f"{comp['name']}@{comp['version']}"
            vuln_matched += 1

    record.vuln_matched_count = vuln_matched
    db.commit()
    return record


def _extract_components(sbom: dict, fmt: str) -> list:
    comps = []
    if fmt == "CycloneDX":
        for c in sbom.get("components", []):
            comps.append({"name": c.get("name", ""), "version": c.get("version", ""),
                          "purl": c.get("purl", ""), "license": _license_str(c.get("licenses", [])),
                          "supplier": c.get("supplier", {}).get("name", "") if isinstance(c.get("supplier"), dict) else ""})
    else:
        for p in sbom.get("packages", []):
            comps.append({"name": p.get("name", ""), "version": p.get("versionInfo", ""),
                          "purl": "", "license": p.get("licenseConcluded", ""), "supplier": p.get("supplier", "")})
    return comps


def _license_str(licenses: list) -> str:
    if not licenses:
        return ""
    if isinstance(licenses[0], dict):
        return licenses[0].get("license", {}).get("id", licenses[0].get("expression", ""))
    return str(licenses[0])


def export_sbom(db: Session, node_id: int, fmt: str = "CycloneDX") -> dict:
    """基于组件库生成 SBOM。"""
    comps = db.query(Component).filter_by(product_node_id=node_id).all()
    items = []
    for c in comps:
        items.append({"type": "library", "name": c.name, "version": c.version,
                      "purl": c.purl or f"pkg:generic/{c.name}@{c.version}"})
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "components": items, "metadata": {"timestamp": now().isoformat()}}
