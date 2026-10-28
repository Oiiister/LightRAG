# LightRAG 环境配置说明

本文基于仓库根目录的 [env.example](env.example) 整理，重点说明各类配置的作用、四类存储与数据库的选择，以及本地测试和工业部署的推荐配置。

核心结论：

- 本地测试使用默认的文件型存储即可，不需要额外数据库。
- 默认存储把主要数据常驻内存，只适合测试、评测和小数据量场景。
- 工业环境优先使用 PostgreSQL 一体化存储。
- 数据规模或专业能力要求更高时，可保留 PostgreSQL 管理 KV 和文档状态，将向量库、图数据库拆分为 Milvus/Qdrant 和 Neo4j/Memgraph。
- 存储后端、Embedding 模型和向量维度应在首次写入文档前确定。

## 1. 配置分组

| 配置组 | 主要变量 | 作用 |
| --- | --- | --- |
| 运行环境 | `LIGHTRAG_RUNTIME_TARGET` | 区分宿主机运行和 Docker/Kubernetes 等 compose 运行。 |
| 服务 | `HOST`、`PORT`、`WORKERS`、`TIMEOUT` | 监听地址、端口、进程数和请求超时。 |
| WebUI | `WEBUI_TITLE`、`WEBUI_DESCRIPTION`、`LIGHTRAG_DEFAULT_UI` | 页面名称、描述，以及根路径默认进入管理端还是查询端。 |
| 鉴权 | `LIGHTRAG_API_KEY`、`AUTH_ACCOUNTS`、`TOKEN_SECRET`、`WHITELIST_PATHS` | API Key、账号登录、JWT 密钥及免鉴权路径。 |
| 跨域 | `CORS_ORIGINS` | 允许哪些浏览器域名跨域调用 API。 |
| HTTPS | `SSL`、`SSL_CERTFILE`、`SSL_KEYFILE` | 服务直接启用 TLS；生产也常在反向代理层终止 TLS。 |
| 目录 | `INPUT_DIR`、`WORKING_DIR`、`LOG_DIR` | 输入文档、文件型存储和日志目录。 |
| 日志 | `LOG_LEVEL`、`VERBOSE`、`LOG_MAX_BYTES`、`LOG_BACKUP_COUNT` | 日志级别、详细程度和轮转策略。 |
| 查询 | `TOP_K`、`CHUNK_TOP_K`、`MAX_ENTITY_TOKENS`、`MAX_RELATION_TOKENS`、`MAX_TOTAL_TOKENS` | 控制知识图谱实体/关系、文本块的召回数量及送入 LLM 的上下文预算。 |
| 查询缓存 | `ENABLE_LLM_CACHE` | 缓存查询阶段的 LLM 结果；流式响应不会使用该缓存。 |
| 向量阈值 | `COSINE_THRESHOLD` | 向量相似度检索的最低阈值。 |
| 文本块选择 | `KG_CHUNK_PICK_METHOD`、`RELATED_CHUNK_NUMBER` | 从知识图谱关联文本中选择块的方式和数量。 |
| 提示词 | `USER_PROMPT_PREFIX`、`USER_PROMPT_PREFIX_FILE` | 给所有查询追加统一的全局指令；文件方式适合较长的提示词。 |
| 重排 | `RERANK_BINDING`、`RERANK_MODEL`、`RERANK_BINDING_HOST`、`MIN_RERANK_SCORE` | 对候选文本块重新排序，提高 `mix`/`hybrid` 查询质量。 |
| 文件解析 | `LIGHTRAG_PARSER`、`MINERU_*`、`DOCLING_*` | 选择 native、legacy、MinerU 或 Docling 解析器及对应服务。 |
| 分块 | `CHUNK_SIZE`、`CHUNK_OVERLAP_SIZE`、`CHUNK_F/R/V/P_*` | 固定长度、递归字符、语义向量或段落语义分块参数。 |
| 抽取 | `ENTITY_EXTRACTION_USE_JSON`、`MAX_EXTRACTION_RECORDS`、`MAX_SOURCE_IDS_PER_ENTITY` | 实体/关系提取格式、单次记录上限和来源追踪上限。 |
| 合并摘要 | `FORCE_LLM_SUMMARY_ON_MERGE`、`SUMMARY_MAX_TOKENS`、`SUMMARY_CONTEXT_SIZE` | 实体/关系描述过长时的摘要触发条件和预算。 |
| LLM | `LLM_BINDING`、`LLM_MODEL`、`LLM_BINDING_HOST`、`LLM_BINDING_API_KEY`、`MAX_ASYNC_LLM` | 主模型、接口地址、密钥和最大并发。 |
| LLM 角色 | `EXTRACT_*`、`KEYWORD_*`、`QUERY_*`、`VLM_*` | 分别覆盖抽取、关键词、查询和视觉模型；未配置时继承全局 LLM。 |
| Embedding | `EMBEDDING_BINDING`、`EMBEDDING_MODEL`、`EMBEDDING_DIM`、`EMBEDDING_BATCH_NUM` | 向量模型、维度、单次批量和最大并发。 |
| 非线性嵌入 | `EMBEDDING_ASYMMETRIC`、`EMBEDDING_DOCUMENT_PREFIX`、`EMBEDDING_QUERY_PREFIX` | 为 BGE/E5/GTE 等模型区分文档和查询前缀。 |
| 流水线 | `MAX_PARALLEL_INSERT`、`MAX_PARALLEL_PARSE_*`、`MAX_PARALLEL_ANALYZE` | 并行处理文档、解析和视觉分析的并发度。 |
| 容量保护 | `MAX_UPLOAD_SIZE`、`MAX_REQUEST_BODY_BYTES`、`MAX_PENDING_DOCUMENTS` | 上传大小、请求体和待处理文档数量上限。 |
| 文件安全 | `DOCX_*`、`PARSER_RESULT_BUNDLE_*`、`NATIVE_MD_IMAGE_*` | 限制 ZIP 炸弹、解析结果和外部图片的体积、数量与超时。 |
| 数据隔离 | `WORKSPACE` | 在同一后端中隔离不同项目或租户的数据。 |
| 存储选择 | `LIGHTRAG_KV_STORAGE`、`LIGHTRAG_VECTOR_STORAGE`、`LIGHTRAG_GRAPH_STORAGE`、`LIGHTRAG_DOC_STATUS_STORAGE` | 分别选择 KV、向量、图和文档状态后端。 |
| 可观测性 | `LANGFUSE_*` | 记录 LLM 调用链，主要用于 OpenAI 兼容接口。 |
| 评测 | `EVAL_*` | RAGAS 评测使用的 LLM、Embedding、并发和超时设置。 |

## 2. 四类存储

LightRAG 把数据拆成四类，分别选择后端：

| 存储类型 | 保存内容 | 本地默认 | 可选生产后端 |
| --- | --- | --- | --- |
| KV | 文档、文本块、LLM 缓存等键值数据 | `JsonKVStorage` | `PGKVStorage`、`RedisKVStorage`、`MongoKVStorage`、`OpenSearchKVStorage` |
| Vector | 实体、关系和文本块的向量 | `NanoVectorDBStorage` | `PGVectorStorage`、`MilvusVectorDBStorage`、`QdrantVectorDBStorage`、`MongoVectorDBStorage`、`OpenSearchVectorDBStorage` |
| Graph | 实体和关系构成的知识图谱 | `NetworkXStorage` | `PGTableGraphStorage`、`Neo4JStorage`、`MemgraphStorage`、`MongoGraphStorage`、`OpenSearchGraphStorage` |
| Doc Status | 文档解析、处理、失败和重试状态 | `JsonDocStatusStorage` | `PGDocStatusStorage`、`RedisDocStatusStorage`、`MongoDocStatusStorage`、`OpenSearchDocStatusStorage` |

默认的 `JsonKVStorage`、`NanoVectorDBStorage`、`NetworkXStorage` 和 `JsonDocStatusStorage` 都在进程内存中保存完整数据，文件仅用于持久化，因此容量受可用内存限制。

## 3. 数据库说明

### 3.1 PostgreSQL

PostgreSQL 是官方推荐的一体化生产后端，可以同时承担全部四类存储。新部署推荐使用：

```env
LIGHTRAG_KV_STORAGE=PGKVStorage
LIGHTRAG_VECTOR_STORAGE=PGVectorStorage
LIGHTRAG_GRAPH_STORAGE=PGTableGraphStorage
LIGHTRAG_DOC_STATUS_STORAGE=PGDocStatusStorage
```

连接配置：

| 变量 | 作用 |
| --- | --- |
| `POSTGRES_HOST`、`POSTGRES_PORT` | 数据库地址和端口。 |
| `POSTGRES_USER`、`POSTGRES_PASSWORD` | 登录凭据。 |
| `POSTGRES_DATABASE` | LightRAG 使用的数据库名。 |
| `POSTGRES_MAX_CONNECTIONS` | 连接池大小，应结合实例规格和多 worker 数量设置。 |
| `POSTGRES_CONNECTION_RETRIES` | 连接重试次数，适合主备切换和短暂网络抖动。 |
| `POSTGRES_CONNECTION_RETRY_BACKOFF` | 初始退避时间。 |
| `POSTGRES_CONNECTION_RETRY_BACKOFF_MAX` | 最大退避时间。 |
| `POSTGRES_POOL_CLOSE_TIMEOUT` | 关闭连接池的超时。 |
| `POSTGRES_SSL_*` | 数据库 TLS、客户端证书和 CA 配置。 |

向量配置：

| 变量 | 作用 |
| --- | --- |
| `POSTGRES_VECTOR_INDEX_TYPE` | `HNSW`、`HNSW_HALFVEC`、`IVFFlat` 或 `VCHORDRQ`。 |
| `POSTGRES_HNSW_M` | HNSW 每个节点的连接数；越高，通常召回更好、内存开销更大。 |
| `POSTGRES_HNSW_EF` | HNSW 查询候选列表大小；越高，召回更好、查询更慢。 |
| `POSTGRES_IVFFLAT_LISTS` | IVFFlat 聚类分区数。 |

写入批处理：

- `POSTGRES_UPSERT_MAX_PAYLOAD_BYTES` 限制单次写入负载大小。
- `POSTGRES_UPSERT_MAX_RECORDS_PER_BATCH` 限制单次写入记录数。
- `POSTGRES_DELETE_MAX_RECORDS_PER_BATCH` 限制单次删除记录数。

图存储应优先选择 `PGTableGraphStorage`，它使用普通索引表和 JSONB，不依赖 Apache AGE，部署更简单且性能优于 `PGGraphStorage`。只有已有 AGE 部署才建议继续使用 `PGGraphStorage`。

PostgreSQL 至少需要启用 `pgvector`。多个 workspace 共享同一向量表时，建议使用 `pgvector 0.8+` 和 HNSW/HNSW_HALFVEC，以避免 workspace 过滤后召回不足。向量维度达到 2000 以上时优先考虑 `HNSW_HALFVEC`。

### 3.2 Milvus

Milvus 适合大规模向量检索，只承担 Vector 存储。

| 变量 | 作用 |
| --- | --- |
| `MILVUS_URI`、`MILVUS_DB_NAME` | Milvus 地址和数据库名。 |
| `MILVUS_USER`、`MILVUS_PASSWORD`、`MILVUS_TOKEN` | 认证信息。 |
| `MILVUS_UPSERT_MAX_PAYLOAD_BYTES` | 单次写入负载上限。 |
| `MILVUS_UPSERT_MAX_RECORDS_PER_BATCH` | 单次写入记录上限。 |
| `MILVUS_DELETE_MAX_RECORDS_PER_BATCH` | 单次删除记录上限。 |
| `MILVUS_INDEX_TYPE` | `AUTOINDEX`、`HNSW`、`HNSW_SQ`、`HNSW_PQ`、`IVF_FLAT`、`IVF_SQ8`、`DISKANN` 等。 |
| `MILVUS_METRIC_TYPE` | `COSINE`、`L2` 或 `IP`。 |
| `MILVUS_HNSW_M`、`MILVUS_HNSW_EF_CONSTRUCTION`、`MILVUS_HNSW_EF` | HNSW 建图和查询参数。 |

选择建议：

- 延迟优先、内存充足：HNSW。
- 需要压缩内存：HNSW_SQ、HNSW_PQ。
- 超大数据、内存受限：DISKANN。
- 不确定时先使用 `AUTOINDEX`，有基准数据后再调整。

### 3.3 Qdrant

Qdrant 适合向量检索和较多 workspace 的场景，只承担 Vector 存储。

| 变量 | 作用 |
| --- | --- |
| `QDRANT_URL` | Qdrant 服务地址。 |
| `QDRANT_API_KEY` | API Key；自建无鉴权环境可省略。 |
| `QDRANT_UPSERT_MAX_PAYLOAD_BYTES` | 单次写入负载上限。 |
| `QDRANT_UPSERT_MAX_POINTS_PER_BATCH` | 单次写入点数上限。 |
| `QDRANT_DELETE_MAX_POINTS_PER_BATCH` | 单次删除点数上限。 |

Qdrant 按 payload 对 workspace 做隔离，并维护租户本地索引。workspace 多且数据分布不均衡时，通常比共享一张 PG 向量表的过滤检索更稳定。

### 3.4 Neo4j

Neo4j 承担 Graph 存储，适合复杂关系查询和成熟图数据库运维体系。

| 变量 | 作用 |
| --- | --- |
| `NEO4J_URI` | `bolt://` 用于单实例，`neo4j://` 或 `neo4j+s://` 用于集群和 Aura 路由。 |
| `NEO4J_USERNAME`、`NEO4J_PASSWORD` | 登录凭据。 |
| `NEO4J_DATABASE` | 图数据库名。 |
| `NEO4J_MAX_CONNECTION_POOL_SIZE` | 连接池大小。 |
| `NEO4J_CONNECTION_TIMEOUT` | 建立连接超时。 |
| `NEO4J_CONNECTION_ACQUISITION_TIMEOUT` | 从连接池获取连接的超时。 |
| `NEO4J_MAX_TRANSACTION_RETRY_TIME` | 事务重试总时长。 |
| `NEO4J_MAX_CONNECTION_LIFETIME` | 连接最长生命周期。 |
| `NEO4J_KEEP_ALIVE` | 保持连接。 |

### 3.5 Memgraph

Memgraph 承担 Graph 存储，兼容 Bolt 协议，适合低延迟图查询。

主要变量为 `MEMGRAPH_URI`、`MEMGRAPH_USERNAME`、`MEMGRAPH_PASSWORD` 和 `MEMGRAPH_DATABASE`。

### 3.6 MongoDB

MongoDB 可以承担全部四类存储，但 `MongoVectorDBStorage` 要求部署支持 Atlas Search/Vector Search，例如 MongoDB Atlas 或支持该能力的本地部署。

主要变量：

- `MONGO_URI`、`MONGO_DATABASE`。
- `MONGO_UPSERT_MAX_PAYLOAD_BYTES`。
- `MONGO_UPSERT_MAX_RECORDS_PER_BATCH`。
- `MONGO_DELETE_MAX_RECORDS_PER_BATCH`。

### 3.7 OpenSearch

OpenSearch 可以承担全部四类存储，适合已经具备搜索集群的团队。

主要变量：

- `OPENSEARCH_HOSTS`、`OPENSEARCH_USER`、`OPENSEARCH_PASSWORD`。
- `OPENSEARCH_USE_SSL`、`OPENSEARCH_VERIFY_CERTS`。
- `OPENSEARCH_NUMBER_OF_SHARDS`、`OPENSEARCH_NUMBER_OF_REPLICAS`。
- `OPENSEARCH_KNN_M`、`OPENSEARCH_KNN_EF_CONSTRUCTION`、`OPENSEARCH_KNN_EF_SEARCH`。
- `OPENSEARCH_USE_PPL_GRAPHLOOKUP`。

三可用区生产集群通常将副本数设为 2。OpenSearch 索引名会被转换为小写；共享集群时，workspace 名称不能只靠大小写区分。

### 3.8 Redis

Redis 可以承担 KV 和 Doc Status 存储，主要变量包括：

- `REDIS_URI`。
- `REDIS_SOCKET_TIMEOUT`、`REDIS_CONNECT_TIMEOUT`。
- `REDIS_MAX_CONNECTIONS`、`REDIS_RETRY_ATTEMPTS`。

LightRAG 会把文档状态、文档信息和调度索引作为持久数据写入 Redis，这些键没有 TTL。Redis 若设置 `maxmemory` 且使用 `allkeys-*` 淘汰策略，可能静默删除文档和调度状态，因此生产环境应使用 `noeviction` 或专用的 Redis 实例/数据库。

## 4. 数据库选型建议

| 场景 | 推荐组合 | 说明 |
| --- | --- | --- |
| 本地开发和小规模测试 | JSON + Nano + NetworkX + JSON Doc Status | 零外部依赖，容量受内存限制。 |
| 通用生产部署 | PostgreSQL 四合一 | 运维最简单，持久化、备份和 HA 体系成熟。 |
| 大规模向量检索 | PostgreSQL KV/Doc Status + Milvus + PGTable/Neo4j | Milvus 承担大规模向量，关系数据仍放在成熟数据库。 |
| 多租户且 workspace 多 | PostgreSQL KV/Doc Status + Qdrant + PGTable/Neo4j | Qdrant 的租户索引可减少 workspace 过滤带来的召回问题。 |
| 复杂图查询 | PostgreSQL KV/Vector/Doc Status + Neo4j | 图操作交给专业图数据库。 |
| 已使用搜索集群 | OpenSearch 四合一 | 降低新增系统的数量，但需要调优分片、副本和 kNN 参数。 |

## 5. 本地简单测试配置

最简单的方式是执行：

```bash
make env-base
```

交互式生成 `.env` 后，将存储保持为默认值：

```env
HOST=127.0.0.1
PORT=9621

INPUT_DIR=./inputs
WORKING_DIR=./rag_storage

LIGHTRAG_KV_STORAGE=JsonKVStorage
LIGHTRAG_VECTOR_STORAGE=NanoVectorDBStorage
LIGHTRAG_GRAPH_STORAGE=NetworkXStorage
LIGHTRAG_DOC_STATUS_STORAGE=JsonDocStatusStorage

ENABLE_LLM_CACHE=true
RERANK_BINDING=null

MAX_ASYNC_LLM=4
EMBEDDING_FUNC_MAX_ASYNC=4
EMBEDDING_BATCH_NUM=16
MAX_PARALLEL_INSERT=2
```

LLM 和 Embedding 至少需要配置：

```env
LLM_BINDING=openai
LLM_BINDING_HOST=https://api.openai.com/v1
LLM_BINDING_API_KEY=替换为真实密钥
LLM_MODEL=替换为可用模型

EMBEDDING_BINDING=openai
EMBEDDING_BINDING_HOST=https://api.openai.com/v1
EMBEDDING_BINDING_API_KEY=替换为真实密钥
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIM=3072
```

由于 `HOST=127.0.0.1`，仅供本机访问，可以暂时不配置鉴权。若改为 `0.0.0.0`，必须配置 `LIGHTRAG_API_KEY` 或 `AUTH_ACCOUNTS`。

这套方案能把数据保存到 `WORKING_DIR`，但完整数据仍主要驻留内存。文档规模增长后，应切换到外部数据库。

## 6. 工业级持久化配置

### 6.1 推荐起点：PostgreSQL 一体化

```env
LIGHTRAG_KV_STORAGE=PGKVStorage
LIGHTRAG_VECTOR_STORAGE=PGVectorStorage
LIGHTRAG_GRAPH_STORAGE=PGTableGraphStorage
LIGHTRAG_DOC_STATUS_STORAGE=PGDocStatusStorage

POSTGRES_HOST=数据库地址
POSTGRES_PORT=5432
POSTGRES_USER=lightrag
POSTGRES_PASSWORD=强密码
POSTGRES_DATABASE=lightrag
POSTGRES_MAX_CONNECTIONS=25

POSTGRES_VECTOR_INDEX_TYPE=HNSW
POSTGRES_HNSW_M=16
POSTGRES_HNSW_EF=200

POSTGRES_CONNECTION_RETRIES=10
POSTGRES_CONNECTION_RETRY_BACKOFF=3.0
POSTGRES_CONNECTION_RETRY_BACKOFF_MAX=30.0

POSTGRES_SSL_MODE=require
```

图存储不要默认使用 `PGGraphStorage`。新部署优先 `PGTableGraphStorage`，并使用启用了 `pgvector` 的 PostgreSQL 镜像或托管实例。

### 6.2 高性能拆分方案

```env
LIGHTRAG_KV_STORAGE=PGKVStorage
LIGHTRAG_DOC_STATUS_STORAGE=PGDocStatusStorage
LIGHTRAG_GRAPH_STORAGE=Neo4JStorage

LIGHTRAG_VECTOR_STORAGE=QdrantVectorDBStorage
# 或：LIGHTRAG_VECTOR_STORAGE=MilvusVectorDBStorage
```

各后端连接示例：

```env
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=lightrag
POSTGRES_PASSWORD=强密码
POSTGRES_DATABASE=lightrag

QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=强密钥

MILVUS_URI=http://milvus:19530
MILVUS_DB_NAME=lightrag
MILVUS_INDEX_TYPE=HNSW
MILVUS_METRIC_TYPE=COSINE

NEO4J_URI=neo4j://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=强密码
NEO4J_DATABASE=neo4j
```

### 6.3 并发与容量

生产并发应服从模型服务限流、数据库连接数和实例内存，不应只调大应用侧数字：

- `MAX_ASYNC_LLM` 控制基础 LLM 并发和单文档抽取 task 数。
- `EXTRACT_MAX_ASYNC_LLM` 可单独限制实际抽取请求。
- `MAX_PARALLEL_INSERT` 控制同时进入抽取和入库阶段的文档数，通常从 2 到 5 逐步调高。
- `MAX_PARALLEL_PARSE_NATIVE`、`MAX_PARALLEL_PARSE_MINERU`、`MAX_PARALLEL_PARSE_DOCLING` 分别控制解析并发。
- `MAX_PENDING_DOCUMENTS` 设置待处理文档上限，生产建议启用，避免无限积压。
- `POSTGRES_MAX_CONNECTIONS` 应结合数据库最大连接数和 worker 数量计算，而不是直接设得很大。

## 7. 上线前必须固定的事项

1. **确定存储后端。** 当前不同存储实现之间没有通用迁移工具。图数据有 `PGGraphStorage` 到 `PGTableGraphStorage` 的专用迁移路径，但不适用于所有后端。
2. **确定 Embedding 模型、维度和非对称前缀。** PostgreSQL 等后端在首次建表时确定向量维度。更换模型或维度需要清空相应 workspace/向量数据并重新索引。
3. **确定 WORKSPACE。** 同一后端服务多个项目时使用不同 workspace 隔离，不要随意混用数据库专用的 `*_WORKSPACE` 覆盖项。
4. **配置鉴权和 TLS。** 对外提供服务时设置 `LIGHTRAG_API_KEY` 或账号鉴权，并配置 HTTPS、CORS 白名单和最小化的免鉴权路径。
5. **准备备份。** 外部数据库必须配置定期备份、恢复测试、监控和容量告警。
6. **保持安全默认值。** `DOCX_MAX_*`、`PARSER_RESULT_BUNDLE_*`、`NATIVE_MD_IMAGE_*` 等限制用于防护异常文件和外部解析服务，除非确认业务文件被误拒，否则不要关闭。

## 8. 快速选择

- 只想本机跑通流程：使用本文第 5 节。
- 要做持久化生产环境但不想维护多种数据库：使用第 6.1 节的 PostgreSQL 四合一。
- 向量规模很大：加入 Milvus。
- 多租户、workspace 多：考虑 Qdrant。
- 复杂关系查询多：加入 Neo4j。
- 已有 MongoDB 或 OpenSearch 运维体系：可以四合一，但首次上线前要验证向量检索能力和容量参数。
