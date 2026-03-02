#!/bin/bash

# 1. 获取 Git 最新 Tag
LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

if [ -z "$LATEST_TAG" ]; then
    echo "Error: No git tags found."
    echo "should_sync=false" >> $GITHUB_OUTPUT
    exit 0
fi

# 2. 从 metadata.yaml 获取当前版本 (匹配 version: v0.0.4 这种格式)
CURRENT_YAML_VER=$(grep "^version:" metadata.yaml | awk '{print $2}' | tr -d '\r')

echo "Latest Tag in Git: $LATEST_TAG"
echo "Current Version in YAML: $CURRENT_YAML_VER"

# 3. 比较并执行更新
if [ "$LATEST_TAG" != "$CURRENT_YAML_VER" ]; then
    echo "Version mismatch detected. Syncing..."
    
    # 准备不带 v 的版本号 (用于 pyproject.toml)
    # 例如 v0.0.5 -> 0.0.5
    PLAIN_VER=$(echo $LATEST_TAG | sed 's/^v//')
    
    # 更新 metadata.yaml
    sed -i "s/^version: .*/version: $LATEST_TAG/" metadata.yaml
    
    # 更新 pyproject.toml (精确匹配 [project] 下的 version)
    sed -i "s/^version = \".*\"/version = \"$PLAIN_VER\"/" pyproject.toml
    
    # 传递变量给 GitHub Actions
    echo "should_sync=true" >> $GITHUB_OUTPUT
    echo "tag_name=$LATEST_TAG" >> $GITHUB_OUTPUT
    echo "Success: Files updated to $LATEST_TAG"
else
    echo "Already in sync. No changes needed."
    echo "should_sync=false" >> $GITHUB_OUTPUT
fi