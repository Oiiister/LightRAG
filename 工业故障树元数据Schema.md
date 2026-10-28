# 工业故障树元数据 Schema

本文定义工业故障树项目的元数据模型。元数据 Schema 规定本体中的每个类和关系需要记录哪些字段、字段类型、必填性、枚举值及校验规则。

## 1. 本体与元数据的关系

```text
本体
  定义有哪些类、允许哪些关系和约束

元数据 Schema
  定义每个类和关系的字段、类型、必填性和校验规则

元数据实例
  保存某个具体部门、文件、设备、故障或关系的数据

知识图谱
  使用审核后的元数据实例构建节点和边
```

例如：

```text
本体：Equipment 可以拥有 HAS_FAULT 关系
Schema：Equipment 必须有 uid、equipment_tag 和 equipment_name
实例：P-101A 是一台冷却水泵
图谱：P-101A --HAS_FAULT--> 出口压力不足
```

## 2. 五类元数据

| 元数据类别 | 对应本体类 | 主要内容 |
| --- | --- | --- |
| 数据资产元数据 | `File` | 文件身份、类型、来源、版本、解析状态 |
| 物理资产元数据 | `Equipment` | 设备身份、位号、厂商、型号、位置 |
| 知识实体元数据 | `FaultEvent` | 故障名称、描述、现象、维修措施 |
| 关系元数据 | `RelationAssertion`、`FaultCauseRule`、`LogicGate` | 关系类型、方向、AND/OR、证据和审核 |
| 证据元数据 | `Evidence` 或证据关系属性 | 文件、Chunk、页码、原文引用 |

`Department` 是组织容器类，也具有自己的元数据。

## 3. 通用实体元数据

所有业务节点共享以下字段。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `uid` | string | 是 | 稳定主键，建议 ULID/UUID |
| `class_code` | enum | 是 | 本体类代码 |
| `tenant_id` | string | 是 | 租户隔离 |
| `canonical_name` | string | 是 | 规范名称 |
| `description` | string | 否 | 描述 |
| `aliases` | string[] | 否 | 别名和同义名称 |
| `ontology_version` | string | 是 | 本体版本 |
| `schema_version` | string | 是 | 元数据 Schema 版本 |
| `review_status` | enum | 是 | 审核状态 |
| `confidence` | number | 否 | 系统计算置信度，范围 0-1 |
| `source_uids` | string[] | 否 | 来源文件或数据来源 |
| `evidence_ids` | string[] | 否 | 支持证据 |
| `valid_from` | datetime | 否 | 生效时间 |
| `valid_to` | datetime | 否 | 失效时间 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |
| `created_by` | string | 是 | 创建人或服务 |

审核状态枚举：

```text
proposed
approved
rejected
merged
deprecated
needs_more_evidence
```

## 4. Department 元数据 Schema

```text
Class: Department
```

| 字段 | 类型 | 必填 | 约束 |
| --- | --- | --- | --- |
| `uid` | string | 是 | 唯一、稳定 |
| `department_code` | string | 否 | 企业内部门编码 |
| `canonical_name` | string | 是 | 同租户内不应重复 |
| `description` | string | 否 | 部门介绍 |
| `department_path` | string | 否 | 可由部门关系计算 |
| `status` | enum | 是 | `active/inactive` |
| `external_refs` | object | 否 | ERP/HR 系统 ID |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

部门与设备、文件的关系：

```text
Department --HAS_EQUIPMENT--> Equipment
Department --OWNS_FILE------> File
Department --HAS_SUB_DEPARTMENT--> Department
```

不要把设备和文件存成部门的数组属性。

## 5. File 元数据 Schema

```text
Class: File
```

### 5.1 基本信息

| 字段 | 类型 | 必填 | 约束 |
| --- | --- | --- | --- |
| `uid` | string | 是 | 文件稳定 ID |
| `file_name` | string | 是 | 原始文件名 |
| `file_extension` | string | 是 | `pdf/docx/xlsx/png/...` |
| `mime_type` | string | 是 | 标准 MIME 类型 |
| `modality` | enum | 是 | `text/table/image/pdf/office` |
| `object_uri` | string | 是 | MinIO/S3/本地对象地址 |
| `checksum` | string | 是 | SHA-256 |
| `file_size` | integer | 是 | 字节数 |
| `version` | string | 否 | 文件版本 |
| `language` | string | 否 | `zh-CN/en/...` |

### 5.2 来源信息

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `source_system` | string | 否 | 上传系统或设备管理系统 |
| `uploader_id` | string | 是 | 上传用户 |
| `upload_time` | datetime | 是 | 上传时间 |
| `external_refs` | object | 否 | 外部文件 ID |

### 5.3 解析信息

| 字段 | 类型 | 必填 | 约束 |
| --- | --- | --- | --- |
| `parse_status` | enum | 是 | `uploaded/parsing/parsed/failed` |
| `parse_engine` | enum | 否 | `native/legacy/mineru/docling` |
| `parse_error` | string | 否 | 失败原因 |
| `page_count` | integer | 否 | 页数 |
| `chunk_count` | integer | 否 | Chunk 数量 |
| `last_parsed_at` | datetime | 否 | 最近解析时间 |

示例：

```json
{
  "uid": "FILE-01J8Z7A2PQ",
  "class_code": "File",
  "tenant_id": "tenant_001",
  "canonical_name": "P-101A设备手册.pdf",
  "file_name": "P-101A设备手册.pdf",
  "file_extension": "pdf",
  "mime_type": "application/pdf",
  "modality": "pdf",
  "object_uri": "s3://lightrag/manuals/P-101A.pdf",
  "checksum": "sha256:...",
  "file_size": 2048000,
  "language": "zh-CN",
  "uploader_id": "user_1001",
  "upload_time": "2026-10-25T10:00:00+08:00",
  "parse_status": "parsed",
  "parse_engine": "native",
  "page_count": 86,
  "review_status": "approved",
  "created_at": "2026-10-25T10:00:00+08:00",
  "updated_at": "2026-10-25T10:20:00+08:00",
  "created_by": "upload_service"
}
```

文件关系：

```text
Department --OWNS_FILE--> File
File --DESCRIBES_EQUIPMENT--> Equipment
File --MENTIONS_FAULT--> FaultEvent
File --PROVIDES_EVIDENCE_FOR--> FaultEvent/FaultCauseRule/LogicGate
```

## 6. Equipment 元数据 Schema

```text
Class: Equipment
```

| 字段 | 类型 | 必填 | 约束 |
| --- | --- | --- | --- |
| `uid` | string | 是 | 设备稳定 ID |
| `equipment_tag` | string | 是 | 如 `P-101A`，租户内唯一 |
| `equipment_name` | string | 是 | 如“冷却水泵” |
| `equipment_type` | string | 是 | 受控设备类型 |
| `aliases` | string[] | 否 | 循环泵、冷却泵等 |
| `manufacturer` | string | 否 | 设备厂商 |
| `model` | string | 否 | 设备型号 |
| `serial_number` | string | 否 | 序列号 |
| `functional_location` | string | 否 | 功能位置 |
| `lifecycle_status` | enum | 是 | `in_service/stopped/retired` |
| `commissioning_date` | date | 否 | 投运日期 |
| `retirement_date` | date | 否 | 退役日期 |
| `external_refs` | object | 否 | ERP/EAM 编号 |
| `source_uids` | string[] | 否 | 支撑设备信息的文件 |
| `review_status` | enum | 是 | 审核状态 |

示例：

```json
{
  "uid": "EQ-P101A",
  "class_code": "Equipment",
  "tenant_id": "tenant_001",
  "canonical_name": "冷却水泵",
  "equipment_tag": "P-101A",
  "equipment_name": "冷却水泵",
  "equipment_type": "PUMP.CENTRIFUGAL",
  "aliases": ["循环泵", "冷却泵"],
  "manufacturer": "Example Co.",
  "model": "CP-200",
  "serial_number": "SN-2024-00931",
  "functional_location": "CN-SH.U1.COOLING",
  "lifecycle_status": "in_service",
  "source_uids": ["FILE-01J8Z7A2PQ"],
  "review_status": "approved",
  "created_at": "2026-10-25T10:00:00+08:00",
  "updated_at": "2026-10-25T10:20:00+08:00",
  "created_by": "asset_service"
}
```

设备关系：

```text
Department --HAS_EQUIPMENT--> Equipment
Equipment --HAS_FAULT--> FaultEvent
```

## 7. FaultEvent 元数据 Schema

```text
Class: FaultEvent
```

| 字段 | 类型 | 必填 | 约束 |
| --- | --- | --- | --- |
| `uid` | string | 是 | 故障事件稳定 ID |
| `fault_name` | string | 是 | 故障名称 |
| `description` | string | 是 | 故障描述 |
| `aliases` | string[] | 否 | 同义名称 |
| `severity` | enum | 否 | `low/medium/high/critical/unknown` |
| `symptoms` | string[] | 否 | 故障现象 |
| `maintenance_measures` | string[] | 否 | 维修或缓解措施 |
| `operating_conditions` | object | 否 | 负载、温度、压力等条件 |
| `active_cause_rule_uid` | string | 否 | 当前生效的因果规则 |
| `source_uids` | string[] | 否 | 来源文件 |
| `evidence_ids` | string[] | 否 | 证据记录 |
| `confidence` | number | 否 | 范围 0-1 |
| `review_status` | enum | 是 | 审核状态 |
| `ontology_version` | string | 是 | 本体版本 |

示例：

```json
{
  "uid": "FAULT-PRESSURE-LOW",
  "class_code": "FaultEvent",
  "tenant_id": "tenant_001",
  "canonical_name": "出口压力不足",
  "fault_name": "出口压力不足",
  "description": "泵出口压力低于正常工作范围",
  "aliases": ["出口压力低", "压力不够"],
  "severity": "high",
  "symptoms": ["压力表读数下降", "系统流量不足"],
  "maintenance_measures": [
    "清理或更换过滤器",
    "检查吸入管密封"
  ],
  "review_status": "approved",
  "ontology_version": "fault-v0.1",
  "schema_version": "metadata-v0.1",
  "created_at": "2026-10-25T10:00:00+08:00",
  "updated_at": "2026-10-25T10:20:00+08:00",
  "created_by": "extract_service"
}
```

不建议把 `TopEvent/IntermediateEvent/BasicEvent` 保存为永久属性，它们应根据当前故障树动态计算。

## 8. FaultCauseRule 元数据 Schema

```text
Class: FaultCauseRule
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `uid` | string | 是 | 规则 ID |
| `effect_fault_uid` | string | 是 | 结果故障 |
| `expression` | object | 是 | 递归 AND/OR 表达式 |
| `scenario` | string | 否 | 适用工况 |
| `evidence_ids` | string[] | 是 | 至少一条证据 |
| `review_status` | enum | 是 | 审核状态 |
| `valid_from` | datetime | 否 | 生效时间 |
| `valid_to` | datetime | 否 | 失效时间 |
| `ontology_version` | string | 是 | 本体版本 |

表达式定义：

```text
Expression =
    EventRef
  | AndExpression
  | OrExpression

EventRef:
  event_uid: string

AndExpression:
  op: "AND"
  children: Expression[]

OrExpression:
  op: "OR"
  children: Expression[]
```

示例：

```json
{
  "uid": "RULE-E-001",
  "class_code": "FaultCauseRule",
  "tenant_id": "tenant_001",
  "effect_fault_uid": "FAULT-E",
  "expression": {
    "op": "AND",
    "children": [
      {
        "op": "OR",
        "children": [
          {"event_uid": "FAULT-A"},
          {"event_uid": "FAULT-B"}
        ]
      },
      {
        "op": "OR",
        "children": [
          {"event_uid": "FAULT-C"},
          {"event_uid": "FAULT-D"}
        ]
      }
    ]
  },
  "evidence_ids": ["EVD-001"],
  "review_status": "approved",
  "ontology_version": "fault-v0.1"
}
```

约束：

- `AND/OR` 至少两个子节点。
- 根表达式不能引用 `effect_fault_uid` 自身。
- 表达式不能成环。
- `EventRef` 必须指向有效 `FaultEvent`。
- 正式规则必须至少有一条证据。

## 9. LogicGate 元数据 Schema

```text
Class: LogicGate
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `uid` | string | 是 | Gate ID |
| `rule_uid` | string | 是 | 来源因果规则 |
| `gate_type` | enum | 是 | `AND/OR` |
| `output_fault_uid` | string | 是 | 输出故障 |
| `input_count` | integer | 是 | 输入数量 |
| `expression_path` | string | 是 | 表达式树路径 |
| `review_status` | enum | 是 | 审核状态 |

约束：

- 每个 Gate 只能有一个输出。
- AND/OR Gate 至少有两个输入。
- Gate 输入可以是 `FaultEvent` 或另一个 `LogicGate`。
- Gate 不能形成环。

## 10. 关系通用元数据 Schema

所有关系共享以下字段。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `relation_uid` | string | 是 | 关系 ID |
| `relation_code` | enum | 是 | 关系类型 |
| `tenant_id` | string | 是 | 租户 |
| `source_uid` | string | 是 | 源对象 |
| `source_type` | enum | 是 | 源类型 |
| `target_uid` | string | 是 | 目标对象 |
| `target_type` | enum | 是 | 目标类型 |
| `direction` | enum | 是 | 固定为 `source_to_target` |
| `properties` | object | 否 | 关系特有属性 |
| `evidence_ids` | string[] | 否 | 证据 ID |
| `confidence` | number | 否 | 范围 0-1 |
| `review_status` | enum | 是 | 审核状态 |
| `valid_from` | datetime | 否 | 生效时间 |
| `valid_to` | datetime | 否 | 失效时间 |
| `ontology_version` | string | 是 | 本体版本 |

## 11. 具体关系 Schema

| `relation_code` | 源类型 | 目标类型 | 特有属性 |
| --- | --- | --- | --- |
| `HAS_SUB_DEPARTMENT` | Department | Department | `valid_from/valid_to` |
| `HAS_EQUIPMENT` | Department | Equipment | `membership_type`、有效期 |
| `OWNS_FILE` | Department | File | `ownership_type`、有效期 |
| `DESCRIBES_EQUIPMENT` | File | Equipment | `coverage` 可选 |
| `MENTIONS_FAULT` | File | FaultEvent | 无额外字段 |
| `PROVIDES_EVIDENCE_FOR` | File | FaultEvent/FaultCauseRule/LogicGate | `evidence_uid` |
| `HAS_FAULT` | Equipment | FaultEvent | `relation_status`、发生时间 |
| `HAS_CAUSE_RULE` | FaultEvent | FaultCauseRule | 无额外字段 |
| `INPUT_OF` | FaultEvent/LogicGate | LogicGate | `input_role` 可选 |
| `OUTPUT_TO` | LogicGate | FaultEvent | 无额外字段 |

`CAUSES` 不单独持久化，由简单 `FaultCauseRule` 或 LogicGate 图推导。

## 12. Evidence 元数据 Schema

如果证据独立存储：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `evidence_uid` | string | 是 | 证据 ID |
| `tenant_id` | string | 是 | 租户 |
| `file_uid` | string | 是 | 来源文件 |
| `chunk_id` | string | 是 | 来源 Chunk |
| `page` | integer | 否 | 页码 |
| `section_path` | string | 否 | 章节 |
| `char_start` | integer | 否 | 原文开始位置 |
| `char_end` | integer | 否 | 原文结束位置 |
| `quote` | string | 是 | 原文精确片段 |
| `quote_hash` | string | 是 | 原文哈希 |
| `supports_uid` | string | 是 | 支持的实体或关系 |
| `supports_type` | enum | 是 | `FaultEvent/FaultCauseRule/LogicGate` |
| `extraction_run_id` | string | 否 | 抽取批次 |
| `review_status` | enum | 是 | 审核状态 |

如果使用关系属性保存证据：

```json
{
  "relation_uid": "REL-002",
  "relation_code": "PROVIDES_EVIDENCE_FOR",
  "source_uid": "FILE-001",
  "source_type": "File",
  "target_uid": "FAULT-PRESSURE-LOW",
  "target_type": "FaultEvent",
  "properties": {
    "page": 38,
    "chunk_id": "chunk-008",
    "section": "4.3 汽蚀",
    "quote": "吸入管漏气且液位过低时，泵发生汽蚀。"
  },
  "review_status": "approved",
  "ontology_version": "fault-v0.1"
}
```

## 13. Schema 校验规则

### 13.1 通用

```text
uid 唯一且稳定
tenant_id 必填
class_code 必须在枚举中
review_status 必须在枚举中
ontology_version 必填
confidence 必须在 0 到 1 之间
```

### 13.2 File

```text
checksum 必填
parse_status 必须是 uploaded/parsing/parsed/failed
parse_status=failed 时可以有 parse_error
parse_status=parsed 时 page_count 和 chunk_count 应可用
```

### 13.3 Equipment

```text
equipment_tag 在租户内唯一
equipment_uid 不随名称或位号变化
lifecycle_status 必须是受控枚举
```

### 13.4 FaultEvent

```text
fault_name 非空
description 非空
不能把维修措施作为故障原因
```

### 13.5 FaultCauseRule

```text
effect_fault_uid 必须存在
expression 必须是合法表达式树
AND/OR 至少两个子节点
正式规则至少有一条证据
```

### 13.6 Relation

```text
source_type/target_type 必须符合关系目录
关系方向固定
正式关系必须有审核状态
有证据要求的关系不能缺少 evidence_ids
```

## 14. 推荐存储表

```text
department
file
equipment
fault_event
fault_cause_rule
logic_gate
relation_assertion
evidence
review_event
ontology_term
```

其中：

- `relation_assertion` 保存所有通用关系。
- `fault_cause_rule` 保存递归 AND/OR 表达式。
- `logic_gate` 保存表达式投影后的门结构。
- `evidence` 可以独立保存，也可以在关系属性中保存。

## 15. 最终关系

```text
Department --HAS_EQUIPMENT--> Equipment
Department --OWNS_FILE--> File
Equipment --HAS_FAULT--> FaultEvent
File --PROVIDES_EVIDENCE_FOR--> FaultEvent
FaultEvent --HAS_CAUSE_RULE--> FaultCauseRule
FaultEvent/LogicGate --INPUT_OF--> LogicGate
LogicGate --OUTPUT_TO--> FaultEvent
```

核心原则：

> **类负责保存对象属性，关系负责保存对象连接；复杂因果统一保存在 `FaultCauseRule.expression` 中，LogicGate 只作为图投影，不重复维护第二套因果事实。**
