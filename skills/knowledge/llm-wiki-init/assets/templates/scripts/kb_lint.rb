#!/usr/bin/env ruby
# frozen_string_literal: true

require "date"
require "digest"
require "pathname"

ROOT = Pathname.new(__dir__).parent.expand_path
CHECK_DIRS = %w[wiki index].freeze
CONTENT_DIRS = %w[raw wiki outputs index assets].freeze
REQUIRED_FRONTMATTER = %w[type status updated].freeze
CANONICAL_TAG = /\A[a-z0-9][a-z0-9-]*\z/
SPECIAL_WIKI_PAGES = %w[
  wiki/index.md
  wiki/overview.md
  wiki/log.md
  wiki/analyses/README.md
  wiki/sources/README.md
  wiki/topics/README.md
  wiki/entities/README.md
  wiki/decisions/README.md
].freeze
DUPLICATE_EXTENSIONS = %w[.md .pdf .m4a .mp4].freeze

def relative(path)
  Pathname.new(path).expand_path.relative_path_from(ROOT).to_s
end

def readable_text(path)
  File.read(path, encoding: "UTF-8", invalid: :replace, undef: :replace)
end

def markdown_without_fenced_code(text)
  in_fence = false
  text.each_line.each_with_object([]) do |line, kept|
    if line.match?(/^\s*(```|~~~)/)
      in_fence = !in_fence
      next
    end
    kept << line unless in_fence
  end.join
end

def wikilink_targets(text)
  markdown_without_fenced_code(text).scan(/\[\[([^\]]+)\]\]/).flatten.map do |raw|
    raw.split("|", 2).first.split("#", 2).first.strip
  end.reject(&:empty?)
end

def frontmatter(text)
  return {} unless text.start_with?("---\n")

  block = text.split(/^---\s*$\n/, 3)[1].to_s
  block.each_line.each_with_object({}) do |line, result|
    match = line.match(/^([A-Za-z0-9_-]+):\s*(.*?)\s*$/)
    result[match[1]] = match[2] if match
  end
end

def frontmatter_tags(text)
  return [] unless text.start_with?("---\n")

  block = text.split(/^---\s*$\n/, 3)[1].to_s
  tags = []
  in_tags = false
  block.each_line do |line|
    if (match = line.match(/^tags:\s*(.*?)\s*$/))
      in_tags = true
      inline = match[1].to_s.gsub(/[\[\]]/, "")
      tags.concat(inline.split(",").map(&:strip).reject(&:empty?))
    elsif in_tags && (match = line.match(/^\s+-\s+["']?(.*?)["']?\s*$/))
      tags << match[1].strip
    elsif in_tags && line.match?(/^\S/)
      in_tags = false
    end
  end
  tags.uniq
end

def all_files
  @all_files ||= Dir.glob(ROOT.join("**", "*"), File::FNM_DOTMATCH)
                    .select { |path| File.file?(path) && !File.symlink?(path) && !relative(path).start_with?(".git/") }
end

def markdown_files
  @markdown_files ||= all_files.select { |path| File.extname(path).downcase == ".md" }
end

def basename_index
  @basename_index ||= all_files.each_with_object(Hash.new { |hash, key| hash[key] = [] }) do |path, index|
    rel = relative(path)
    index[File.basename(rel)] << rel
    index[File.basename(rel, File.extname(rel))] << rel
  end
end

def resolve_target(target, source)
  return [] if target.match?(%r{\A[a-z]+://}i)

  candidates = []
  if target.include?("/")
    candidates << target
    candidates << "#{target}.md" if File.extname(target).empty?

    source_dir = File.dirname(source)
    relative_target = Pathname.new(source_dir).join(target).cleanpath.to_s
    candidates << relative_target
    candidates << "#{relative_target}.md" if File.extname(relative_target).empty?
  else
    candidates.concat(basename_index[target])
    candidates.concat(basename_index["#{target}.md"]) if File.extname(target).empty?
  end

  candidates.uniq.select { |candidate| File.file?(ROOT.join(candidate)) }
end

def print_stats
  puts "Knowledge base snapshot"
  CONTENT_DIRS.each do |dir|
    paths = Dir.glob(ROOT.join(dir, "**", "*"), File::FNM_DOTMATCH)
               .select { |path| File.file?(path) && !File.symlink?(path) }
    markdown_count = paths.count { |path| File.extname(path).downcase == ".md" }
    bytes = paths.sum { |path| File.size(path) }
    puts format("  %-8s files=%-5d markdown=%-5d size=%s", dir, paths.size, markdown_count, human_size(bytes))
  end
end

def human_size(bytes)
  units = %w[B KiB MiB GiB TiB]
  value = bytes.to_f
  unit = units.shift
  while value >= 1024 && !units.empty?
    value /= 1024
    unit = units.shift
  end
  value >= 10 || unit == "B" ? format("%.0f%s", value, unit) : format("%.1f%s", value, unit)
end

def check_frontmatter
  problems = []
  warnings = []
  Dir.glob(ROOT.join("wiki", "**", "*.md")).sort.each do |path|
    rel = relative(path)
    metadata = frontmatter(readable_text(path))
    missing = REQUIRED_FRONTMATTER.reject { |key| metadata.key?(key) && !metadata[key].empty? }
    problems << "#{rel}: missing #{missing.join(', ')}" unless missing.empty?

    optional_missing = %w[title summary].reject { |key| metadata.key?(key) && !metadata[key].empty? }
    warnings << "#{rel}: optional #{optional_missing.join(', ')} missing" unless optional_missing.empty?

    next unless metadata["status"] == "current" && metadata["updated"]&.match?(/\A\d{4}-\d{2}-\d{2}\z/)

    age = Date.today - Date.iso8601(metadata["updated"])
    warnings << "#{rel}: current but not updated for #{age.to_i} days" if age > 120
  rescue Date::Error
    problems << "#{rel}: invalid updated date #{metadata['updated'].inspect}"
  end
  [problems, warnings]
end

def check_tags
  problems = []
  warnings = []
  usage = Hash.new(0)

  Dir.glob(ROOT.join("wiki", "**", "*.md")).sort.each do |path|
    rel = relative(path)
    tags = frontmatter_tags(readable_text(path))
    if tags.empty?
      problems << "#{rel}: missing tags"
      next
    end

    tags.each do |tag|
      usage[tag] += 1
      problems << "#{rel}: non-canonical tag #{tag.inspect}" unless tag.match?(CANONICAL_TAG)
    end
    warnings << "#{rel}: more than 8 tags" if tags.size > 8
  end
  [problems, warnings, usage]
end

def check_links
  broken = []
  ambiguous = []
  files = CHECK_DIRS.flat_map { |dir| Dir.glob(ROOT.join(dir, "**", "*.md")) }.uniq.sort

  files.each do |path|
    source = relative(path)
    wikilink_targets(readable_text(path)).each do |target|
      resolved = resolve_target(target, source)
      broken << "#{source}: [[#{target}]]" if resolved.empty?
      ambiguous << "#{source}: [[#{target}]] -> #{resolved.join(', ')}" if resolved.size > 1
    end
  end
  [broken, ambiguous]
end

def check_index
  wiki_files = Dir.glob(ROOT.join("wiki", "**", "*.md")).map { |path| relative(path) }.sort
  texts = wiki_files.to_h { |rel| [rel, readable_text(ROOT.join(rel))] }
  incoming = Hash.new(0)

  texts.each do |source, text|
    wikilink_targets(text).each do |target|
      resolve_target(target, source).each { |resolved| incoming[resolved] += 1 if resolved.end_with?(".md") }
    end
  end

  index_targets = wikilink_targets(readable_text(ROOT.join("wiki/index.md"))).flat_map do |target|
    resolve_target(target, "wiki/index.md")
  end.to_h { |target| [target, true] }

  candidates = wiki_files - SPECIAL_WIKI_PAGES
  orphans = candidates.select { |path| incoming[path].zero? }
  absent = candidates.reject { |path| index_targets[path] }
  [orphans, absent]
end

def check_duplicates
  candidates = all_files.select { |path| DUPLICATE_EXTENSIONS.include?(File.extname(path).downcase) }
  groups = Hash.new { |hash, key| hash[key] = [] }

  candidates.each do |path|
    key = [File.size(path), Digest::SHA1.file(path).hexdigest]
    groups[key] << relative(path)
  end

  duplicates = groups.select { |_key, paths| paths.size > 1 }
  reclaimable = duplicates.sum { |(size, _digest), paths| size * (paths.size - 1) }
  puts "Duplicate scan: groups=#{duplicates.size}, files=#{duplicates.values.sum(&:size)}, reclaimable=#{human_size(reclaimable)}"
  duplicates.sort_by { |(size, _digest), paths| -(size * (paths.size - 1)) }.first(20).each do |(size, _digest), paths|
    puts "  #{paths.size} copies, #{human_size(size * (paths.size - 1))} reclaimable"
    paths.each { |path| puts "    - #{path}" }
  end
end

stats_only = ARGV.delete("--stats-only")
duplicates = ARGV.delete("--duplicates")
help = ARGV.delete("--help") || ARGV.delete("-h")

if help
  puts <<~HELP
    Usage: ruby scripts/kb_lint.rb [--stats-only] [--duplicates]

      --stats-only   Print current directory statistics without lint checks.
      --duplicates   Include the slower duplicate-content scan.
  HELP
  exit 0
end

Dir.chdir(ROOT)
print_stats
exit 0 if stats_only

frontmatter_problems, frontmatter_warnings = check_frontmatter
tag_problems, tag_warnings, tag_usage = check_tags
broken_links, ambiguous_links = check_links
orphans, absent_from_index = check_index

puts "Lint summary"
puts "  frontmatter_errors=#{frontmatter_problems.size}"
puts "  tag_errors=#{tag_problems.size}"
puts "  unique_wiki_tags=#{tag_usage.size}"
puts "  broken_links=#{broken_links.size}"
puts "  ambiguous_links=#{ambiguous_links.size}"
puts "  orphan_wiki_pages=#{orphans.size}"
puts "  absent_from_main_index=#{absent_from_index.size}"
puts "  warnings=#{frontmatter_warnings.size + tag_warnings.size}"

{
  "Frontmatter errors" => frontmatter_problems,
  "Tag errors" => tag_problems,
  "Broken links" => broken_links,
  "Ambiguous links" => ambiguous_links,
  "Orphan wiki pages" => orphans,
  "Pages absent from wiki/index.md" => absent_from_index,
  "Warnings" => frontmatter_warnings + tag_warnings
}.each do |title, items|
  next if items.empty?

  puts "#{title}:"
  items.each { |item| puts "  - #{item}" }
end

check_duplicates if duplicates

error_count = frontmatter_problems.size + tag_problems.size + broken_links.size + orphans.size + absent_from_index.size
exit(error_count.zero? ? 0 : 1)
