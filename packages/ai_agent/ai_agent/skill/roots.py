from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path


class SkillRootsSandbox:
    """
    将相对路径限定在若干已命名的技能根目录内。

    引用须为 ``{root_key}/{skill_id}`` 两段，skill_id 对应根下子文件夹。

    Args:
        roots: 根键到目录绝对路径的映射；至少一项
    """

    def __init__(self, roots: Mapping[str, Path | str]) -> None:
        if not roots:
            raise ValueError("至少需要一个 skill 根目录")
        self._roots: dict[str, Path] = {}
        for key, raw in roots.items():
            label = key.strip()
            if not label:
                raise ValueError("root 名称不能为空")
            if label in self._roots:
                raise ValueError(f"重复的 root 名称: {label}")
            root = Path(raw).expanduser().resolve()
            root.mkdir(parents=True, exist_ok=True)
            if not root.is_dir():
                raise ValueError(f"skill 根须为目录: {label}")
            self._roots[label] = root

    @property
    def root_keys(self) -> tuple[str, ...]:
        return tuple(self._roots.keys())

    def root_path(self, root_key: str) -> Path:
        """返回某根目录的绝对路径（供应用侧使用，勿写入模型可见文案）。"""
        return self._roots[self._require_root(root_key)]

    def require_root(self, root_key: str) -> str:
        """校验并返回根键。"""
        return self._require_root(root_key)

    def _require_root(self, root_key: str) -> str:
        cleaned = root_key.strip()
        if cleaned not in self._roots:
            known = ", ".join(sorted(self._roots))
            raise ValueError(f"未知 root: {root_key}（可用: {known}）")
        return cleaned

    def parse_ref(self, skill_ref: str) -> tuple[str, str, Path]:
        """
        解析 skill 引用为 (root_key, skill_id, skill_dir)。

        Args:
            skill_ref: ``{root_key}/{skill_id}`` 形式

        Returns:
            根键、技能目录名、技能目录绝对路径
        """
        root_key, skill_id = self._split_skill_ref(skill_ref)
        return root_key, skill_id, self._skill_dir(root_key, skill_id)

    def _split_skill_ref(self, skill_ref: str) -> tuple[str, str]:
        cleaned = skill_ref.strip().strip("/")
        if not cleaned:
            raise ValueError("skill_ref 不能为空")
        parts = cleaned.split("/")
        if len(parts) != 2:
            raise ValueError(
                "skill_ref 须为 {root_key}/{skill_id} 形式，例如 skills/demo-skill"
            )
        root_key = self._require_root(parts[0])
        skill_id = parts[1].strip()
        if not skill_id or skill_id in (".", ".."):
            raise ValueError(f"非法 skill_id: {parts[1]}")
        return root_key, skill_id

    def _skill_dir(self, root_key: str, skill_id: str) -> Path:
        root = self._roots[root_key]
        target = (root / skill_id).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"skill_id 越出根目录: {skill_id}") from exc
        return target

    def resolve_path(self, skill_ref: str, rel_path: str = "") -> Path:
        """
        解析技能目录内的相对路径。

        Args:
            skill_ref: ``{root_key}/{skill_id}``
            rel_path: 相对技能目录的路径；空则返回技能目录本身

        Returns:
            解析后的绝对路径
        """
        root_key, skill_id = self._split_skill_ref(skill_ref)
        skill_root = self._skill_dir(root_key, skill_id)
        if not rel_path.strip():
            return skill_root
        cleaned = rel_path.strip().lstrip("/")
        if Path(cleaned).is_absolute():
            raise ValueError("rel_path 须为相对路径")
        if ".." in Path(cleaned).parts:
            raise ValueError(f"非法 rel_path: {rel_path}")
        target = (skill_root / cleaned).resolve()
        try:
            target.relative_to(skill_root)
        except ValueError as exc:
            raise ValueError(f"路径越出技能目录: {rel_path}") from exc
        return target

    def skill_md_path(self, skill_ref: str) -> Path:
        """返回 SKILL.md 的绝对路径。"""
        root_key, skill_id = self._split_skill_ref(skill_ref)
        return self._skill_dir(root_key, skill_id) / "SKILL.md"


def normalize_skill_roots(
    roots: Mapping[str, Path | str] | Sequence[Path | str] | Path | str,
) -> dict[str, Path | str]:
    """
    将多种入参形态规范为 ``{root_key: path}``。

    Args:
        roots: 映射、路径列表或单一路径

    Returns:
        根键到路径的映射
    """
    if isinstance(roots, Mapping):
        return dict(roots)
    if isinstance(roots, (str, Path)):
        path = Path(roots)
        label = path.name or "skills"
        return {label: roots}
    items = list(roots)
    if not items:
        raise ValueError("skill 根目录列表不能为空")
    result: dict[str, Path | str] = {}
    for index, raw in enumerate(items):
        path = Path(raw)
        label = path.name or f"root_{index}"
        if label in result:
            label = f"{label}_{index}"
        result[label] = raw
    return result
