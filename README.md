# ERPNext SRM Portal (MVP)

目标：在 ERPNext v16 上提供供应商门户（Supplier ASN、序列管理、打印、ASN->PR）。

快速安装（开发环境）：
1. 在 bench 环境下把本仓库复制到 bench/apps/ 或使用 git clone，然后运行：
   bench new-app erpnext_srm_portal  # 可手动创建 app 并复制文件到该目录
2. 安装 app 到站点：
   bench --site your-site install-app erpnext_srm_portal
3. 在 Desk 中导入 DocType JSON 或运行 migrate：
   bench --site your-site migrate

MVP 功能：
- Supplier ASN Web 提交（示例网页）
- 强校验：ASN 必须带序列/批次
- 序列生成/打印记录（Serial Pool）
- ASN 审批通过自动生成 Purchase Receipt 并带序列

开发说明与注意事项：
- Website User（portal user）交互应通过 Web Forms / Website pages / whitelist APIs 实现，避免授予 system user 权限。
- 需要在 Desk 中根据业务配置 Workflow（Supplier ASN 的审批流）并把审批动作与 submit_asn_and_create_purchase_receipt 触发绑定。
- Serial Pool 需要对 serial 字段建立唯一索引以防止重复。

下一步我将：
- 提交这些文件到 feat/srm-mvp 分支并打开 PR 到 main（包含安装说明与测试要点）。
- 在 PR 中添加示例数据与更详细的权限/workflow 建议。
