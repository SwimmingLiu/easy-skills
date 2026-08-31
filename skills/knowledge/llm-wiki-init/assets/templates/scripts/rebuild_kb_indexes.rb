#!/usr/bin/env ruby
# frozen_string_literal: true

require "date"
require "pathname"
require "yaml"

ROOT = Pathname.new(__dir__).parent.expand_path
TODAY = Date.today.iso8601
GENERATED = %w[
  index/skills.md
  wiki/indexes/wiki-catalog.md
  wiki/indexes/tag-index.md
  wiki/indexes/raw-status.md
  wiki/indexes/output-status.md
].freeze

TAG_ALIASES = {
  "AI" => "ai",
  "AI-assistant" => "ai-assistant",
  "AI-engineering" => "ai-engineering",
  "AI-native" => "ai-native",
  "CLI" => "cli",
  "LLM" => "llm",
  "MCP" => "mcp",
  "ai engineering" => "ai-engineering",
  "coding agents" => "coding-agent",
  "agents" => "agent",
  "analyses" => "analysis",
  "decisions" => "decision",
  "entities" => "entity",
  "eval" => "evaluation",
  "evals" => "evaluation",
  "harness" => "harness-engineering",
  "orchestration" => "agent-orchestration",
  "skills" => "agent-skills",
  "sources" => "source",
  "topics" => "topic"
}.freeze

TYPE_ORDER = %w[topic analysis source entity decision index overview log].freeze

def relative(path)
  Pathname.new(path).expand_path.relative_path_from(ROOT).to_s
end

def read_text(path)
  File.read(path, encoding: "UTF-8", invalid: :replace, undef: :replace)
end

def frontmatter_data(path)
  text = read_text(path)
  return [{}, text] unless text.start_with?("---\n")

  block = text.split(/^---\s*$\n/, 3)[1].to_s
  data = YAML.safe_load(block, permitted_classes: [Date, Time], aliases: true) || {}
  [data.transform_keys(&:to_s), text]
rescue Psych::SyntaxError => error
  warn "Cannot parse #{relative(path)}: #{error.message.lines.first.strip}"
  [{}, text]
end

def tags_for(data)
  Array(data["tags"]).map(&:to_s).map(&:strip).reject(&:empty?).uniq
end

def title_for(data, path)
  data["title"].to_s.strip.empty? ? File.basename(path, ".md") : data["title"].to_s.strip
end

def wiki_link(path, title = nil)
  target = relative(path).sub(/\.md\z/, "")
  label = title.to_s.gsub("|", "-")
  label.empty? ? "[[#{target}]]" : "[[#{target}|#{label}]]"
end

def escape_cell(value)
  value.to_s.gsub("|", "\\|").gsub(/\s+/, " ").strip
end

def human_size(bytes)
  units = %w[B KiB MiB GiB TiB]
  value = bytes.to_f
  unit = units.shift
  while value >= 1024 && !units.empty?
    value /= 1024
    unit = units.shift
  end
  value >= 10 || unit == "B" ? format("%.0f %s", value, unit) : format("%.1f %s", value, unit)
end

def replace_tags(text, tags)
  block = "tags:\n" + tags.map { |tag| "  - #{tag}\n" }.join
  text.sub(/^tags:\s*.*\n(?:\s+-\s+.*\n)*/, block)
end

def normalize_wiki_tags
  changed = []
  Dir.glob(ROOT.join("wiki", "**", "*.md")).sort.each do |path|
    data, text = frontmatter_data(path)
    tags = tags_for(data)
    next if tags.empty?

    normalized = tags.map { |tag| TAG_ALIASES.fetch(tag, tag) }.uniq
    next if normalized == tags

    File.write(path, replace_tags(text, normalized))
    changed << relative(path)
  end
  puts "Normalized tags in #{changed.size} Wiki pages."
end

def raw_bucket_rows
  roots = Dir.children(ROOT.join("raw")).sort.map { |name| ROOT.join("raw", name) }
  directories = roots.select(&:directory?)
  rows = directories.map do |directory|
    files = Dir.glob(directory.join("**", "*"), File::FNM_DOTMATCH).select do |path|
      File.file?(path) && File.basename(path) != ".gitkeep"
    end
    markdown_count = files.count { |path| File.extname(path).downcase == ".md" }
    latest = files.empty? ? "-" : files.map { |path| File.mtime(path).to_date }.max.iso8601
    [directory.basename.to_s, markdown_count, files.size, human_size(files.sum { |path| File.size(path) }), latest]
  end

  root_files = Dir.glob(ROOT.join("raw", "*"), File::FNM_DOTMATCH).select do |path|
    File.file?(path) && File.basename(path) != ".gitkeep"
  end
  unless root_files.empty?
    markdown_count = root_files.count { |path| File.extname(path).downcase == ".md" }
    rows << ["(root)", markdown_count, root_files.size, human_size(root_files.sum { |path| File.size(path) }), root_files.map { |path| File.mtime(path).to_date }.max.iso8601]
  end
  rows
end

def write_raw_status
  rows = raw_bucket_rows
  markdown_total = rows.sum { |row| row[1] }
  file_total = rows.sum { |row| row[2] }
  body = +<<~MARKDOWN
    ---
    title: Raw Source Status
    type: index
    status: current
    date: #{TODAY}
    updated: #{TODAY}
    tags:
      - raw
      - inventory
    summary: 原始资料目录级库存、体积和最近改动的机器生成索引。
    ---

    # Raw Source Status

    > 自动生成于 #{TODAY}。运行 `ruby scripts/rebuild_kb_indexes.rb` 可刷新。本页只统计库存；来源价值、可靠性和编译关系记录在对应的 `wiki/sources/` 页面中。

    | 目录 | Markdown | 全部文件 | 体积 | 最近改动 |
    | --- | ---: | ---: | ---: | --- |
  MARKDOWN
  rows.each do |row|
    directory = row[0] == "(root)" ? "raw/（根目录文件）" : "raw/#{row[0]}/"
    body << "| `#{directory}` | #{row[1]} | #{row[2]} | #{row[3]} | #{row[4]} |\n"
  end
  body << "| **合计** | **#{markdown_total}** | **#{file_total}** | — | — |\n"
  body << <<~MARKDOWN

    ## 编译状态

    - `unreviewed`：尚未检查。
    - `indexed`：已登记基本元数据。
    - `summarized`：已有 `wiki/sources/` 摘要。
    - `compiled`：已回流到主题、实体或分析页。
    - `low-value`：保留原文，但暂不投入整理。

    ## 相关入口

    - [[wiki/index|精选 Wiki 导航]]
    - [[wiki/indexes/wiki-catalog|完整 Wiki 目录]]
    - [[wiki/indexes/tag-index|Wiki 标签索引]]
    - [[index/home|知识库首页]]
  MARKDOWN
  File.write(ROOT.join("wiki/indexes/raw-status.md"), body)
end

def output_bucket_rows
  roots = Dir.children(ROOT.join("outputs")).sort.map { |name| ROOT.join("outputs", name) }
  directories = roots.select(&:directory?)
  rows = directories.map do |directory|
    files = Dir.glob(directory.join("**", "*"), File::FNM_DOTMATCH).select do |path|
      File.file?(path) && File.basename(path) != ".gitkeep"
    end
    markdown = files.select { |path| File.extname(path).downcase == ".md" }
    with_frontmatter = 0
    tagged = 0
    statuses = Hash.new(0)
    markdown.each do |path|
      data, text = frontmatter_data(path)
      with_frontmatter += 1 if text.start_with?("---\n")
      tagged += 1 unless tags_for(data).empty?
      status = data["status"].to_s.strip
      statuses[status] += 1 unless status.empty?
    end
    latest = files.empty? ? "-" : files.map { |path| File.mtime(path).to_date }.max.iso8601
    status_text = statuses.empty? ? "未声明" : statuses.sort.map { |key, value| "#{key}: #{value}" }.join("; ")
    [directory.basename.to_s, markdown.size, files.size, human_size(files.sum { |path| File.size(path) }), with_frontmatter, tagged, status_text, latest]
  end

  root_files = Dir.glob(ROOT.join("outputs", "*"), File::FNM_DOTMATCH).select do |path|
    File.file?(path) && File.basename(path) != ".gitkeep"
  end
  unless root_files.empty?
    markdown = root_files.select { |path| File.extname(path).downcase == ".md" }
    rows << ["(root)", markdown.size, root_files.size, human_size(root_files.sum { |path| File.size(path) }), 0, 0, "未声明", root_files.map { |path| File.mtime(path).to_date }.max.iso8601]
  end
  rows
end

def write_output_status
  rows = output_bucket_rows
  markdown_total = rows.sum { |row| row[1] }
  file_total = rows.sum { |row| row[2] }
  frontmatter_total = rows.sum { |row| row[4] }
  tagged_total = rows.sum { |row| row[5] }
  body = +<<~MARKDOWN
    ---
    title: Outputs 状态索引
    type: index
    status: current
    date: #{TODAY}
    updated: #{TODAY}
    tags:
      - index
      - outputs
      - lifecycle
    summary: Outputs 派生产物的目录级完整清单、元数据覆盖率和生命周期治理规则。
    ---

    # Outputs 状态索引

    > 自动生成于 #{TODAY}。本页覆盖 `outputs/` 下的全部一级目录；运行 `ruby scripts/rebuild_kb_indexes.rb` 可刷新。派生产物按目录导航，不要求每个历史文件都进入 Wiki 主索引。

    ## 目录总览

    | 目录 | Markdown | 全部文件 | 体积 | 有 frontmatter | 有 tags | 已声明状态 | 最近改动 |
    | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
  MARKDOWN
  rows.each do |row|
    directory = row[0] == "(root)" ? "outputs/（根目录文件）" : "outputs/#{row[0]}/"
    body << "| `#{directory}` | #{row[1]} | #{row[2]} | #{row[3]} | #{row[4]} | #{row[5]} | #{escape_cell(row[6])} | #{row[7]} |\n"
  end
  body << "| **合计** | **#{markdown_total}** | **#{file_total}** | — | **#{frontmatter_total}** | **#{tagged_total}** | — | — |\n"
  body << <<~MARKDOWN

    ## 生命周期规则

    - `outputs/` 保存任务交付，不以“全部打标签”作为完成标准；主要导航依赖目录、文件名和全文搜索。
    - 新产物建议使用 `status: draft | final | historical | promoted`；重要成品至少补 `title`、`type`、`status`、`updated`、`tags` 和 `summary`。
    - 有长期复用价值的结论应拆解并晋升到 `wiki/topics/`、`wiki/analyses/` 或相关主题页，同时在原输出中留下“已沉淀到”链接。
    - 同一任务的中间版本保留在原目录；只有确认无引用且可恢复时才做删除或归档。

    ## 相关入口

    - [[index/home|知识库首页]]
    - [[wiki/indexes/wiki-catalog|完整 Wiki 目录]]
    - [[wiki/indexes/tag-index|Wiki 标签索引]]
    - [[wiki/indexes/raw-status|Raw 状态索引]]
  MARKDOWN
  File.write(ROOT.join("wiki/indexes/output-status.md"), body)
end

def skill_metadata(path)
  text = read_text(path)
  block = text[/\A---\s*\n(.*?)\n---\s*\n/m, 1].to_s
  data = YAML.safe_load(block, permitted_classes: [Date, Time], aliases: true) || {}
  [data["name"].to_s.strip, data["description"].to_s.gsub(/\s+/, " ").strip]
rescue Psych::SyntaxError
  [block[/^name:\s*["']?(.*?)["']?\s*$/, 1].to_s, block[/^description:\s*["']?(.*?)["']?\s*$/, 1].to_s]
end

def write_skill_index
  skill_root = ROOT.join("skills")
  records = Dir.glob(skill_root.join("**", "SKILL.md")).sort.map do |path|
    name, description = skill_metadata(path)
    relative_skill = Pathname.new(path).relative_path_from(skill_root).to_s
    [name.empty? ? File.basename(File.dirname(path)) : name, description, relative_skill]
  end
  body = +<<~MARKDOWN
    ---
    title: 已安装 Skills 索引
    type: index
    status: current
    date: #{TODAY}
    updated: #{TODAY}
    tags:
      - index
      - agent-skills
    count: #{records.size}
    summary: 当前知识库随附 Skills 的机器生成完整清单。
    ---

    # 已安装 Skills 索引

    > 自动生成于 #{TODAY}，共发现 #{records.size} 个 `SKILL.md`。运行 `ruby scripts/rebuild_kb_indexes.rb` 可刷新。

    | Skill | 说明 | 定义文件 |
    | --- | --- | --- |
  MARKDOWN
  records.sort_by { |name, _description, path| [name.downcase, path] }.each do |name, description, path|
    body << "| `#{escape_cell(name)}` | #{escape_cell(description)} | `skills/#{escape_cell(path)}` |\n"
  end
  body << <<~MARKDOWN

    ## 相关入口

    - [[wiki/indexes/tag-index|Wiki 标签索引]]
    - [[index/home|知识库首页]]
  MARKDOWN
  File.write(ROOT.join("index/skills.md"), body)
end

def wiki_records
  Dir.glob(ROOT.join("wiki", "**", "*.md")).sort.each_with_object([]) do |path, records|
    next if relative(path) == "wiki/indexes/wiki-catalog.md"

    data, = frontmatter_data(path)
    records << {
      path: path,
      title: title_for(data, path),
      type: data["type"].to_s.strip.empty? ? "unknown" : data["type"].to_s.strip,
      status: data["status"].to_s.strip.empty? ? "unknown" : data["status"].to_s.strip,
      updated: data["updated"].to_s.strip.empty? ? "-" : data["updated"].to_s.strip,
      summary: data["summary"].to_s,
      tags: tags_for(data)
    }
  end
end

def write_tag_index(records)
  by_tag = Hash.new { |hash, key| hash[key] = [] }
  records.each { |record| record[:tags].each { |tag| by_tag[tag] << record } }
  body = +<<~MARKDOWN
    ---
    title: Wiki 标签索引
    type: index
    status: current
    date: #{TODAY}
    updated: #{TODAY}
    tags:
      - index
      - tag-system
    summary: Wiki 层全部规范标签的词表、使用频次和反向页面入口。
    ---

    # Wiki 标签索引

    > 自动生成于 #{TODAY}，覆盖 #{records.size} 个 Wiki 页面、#{by_tag.size} 个标签。运行 `ruby scripts/rebuild_kb_indexes.rb --normalize-tags` 可先归一化别名，再重建本页。

    ## 使用规则

    - 标签统一使用小写 `kebab-case`，例如 `coding-agent`、`context-engineering`。
    - `type` 管页面类型，`status` 管生命周期，标签只表达可跨页面检索的主题、对象或方法。
    - 优先复用已有标签；只有新概念会持续连接多个页面时才新增标签。
    - `raw/` 和 `outputs/` 以路径、来源和全文检索为主；本页只治理可复用的 Wiki 层。

    ## 完整标签表

    | 标签 | 页面数 | 页面 |
    | --- | ---: | --- |
  MARKDOWN
  by_tag.sort_by { |tag, records_for_tag| [-records_for_tag.size, tag] }.each do |tag, tagged_records|
    links = tagged_records.sort_by { |record| record[:title].downcase }.map { |record| wiki_link(record[:path], record[:title]) }.join("<br>")
    body << "| `#{tag}` | #{tagged_records.size} | #{links} |\n"
  end
  body << <<~MARKDOWN

    ## 相关入口

    - [[wiki/indexes/wiki-catalog|完整 Wiki 目录]]
    - [[wiki/indexes/raw-status|Raw 状态索引]]
    - [[wiki/indexes/output-status|Outputs 状态索引]]
    - [[index/home|知识库首页]]
  MARKDOWN
  File.write(ROOT.join("wiki/indexes/tag-index.md"), body)
end

def write_wiki_catalog(records)
  groups = records.group_by { |record| record[:type] }
  ordered_types = TYPE_ORDER + (groups.keys - TYPE_ORDER).sort
  body = +<<~MARKDOWN
    ---
    title: 完整 Wiki 目录
    type: index
    status: current
    date: #{TODAY}
    updated: #{TODAY}
    tags:
      - index
      - wiki
      - catalog
    summary: Wiki 层所有页面按类型汇总的机器生成完整目录。
    ---

    # 完整 Wiki 目录

    > 自动生成于 #{TODAY}，共收录 #{records.size} 个页面（不含本页）。运行 `ruby scripts/rebuild_kb_indexes.rb` 可刷新。`wiki/index.md` 负责精选导航，本页负责完整覆盖。
  MARKDOWN
  ordered_types.each do |type|
    typed_records = groups[type]
    next if typed_records.nil? || typed_records.empty?

    body << "\n## #{type}（#{typed_records.size}）\n\n"
    body << "| 页面 | 状态 | 更新 | 标签 | 摘要 |\n| --- | --- | --- | --- | --- |\n"
    typed_records.sort_by { |record| record[:title].downcase }.each do |record|
      tags = record[:tags].map { |tag| "`#{tag}`" }.join(" ")
      body << "| #{wiki_link(record[:path], record[:title])} | #{escape_cell(record[:status])} | #{record[:updated]} | #{tags} | #{escape_cell(record[:summary])} |\n"
    end
  end
  body << <<~MARKDOWN

    ## 相关入口

    - [[wiki/index|精选 Wiki 导航]]
    - [[wiki/indexes/tag-index|Wiki 标签索引]]
    - [[wiki/indexes/raw-status|Raw 状态索引]]
    - [[wiki/indexes/output-status|Outputs 状态索引]]
  MARKDOWN
  File.write(ROOT.join("wiki/indexes/wiki-catalog.md"), body)
end

Dir.chdir(ROOT)
normalize_wiki_tags if ARGV.delete("--normalize-tags")
write_skill_index
write_raw_status
write_output_status
records = wiki_records
write_tag_index(records)
records = wiki_records
write_wiki_catalog(records)
puts "Rebuilt #{GENERATED.join(', ')}."
