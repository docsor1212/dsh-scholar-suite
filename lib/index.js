// dsh-scholar-suite — SkillHub 学术工具链 8 技能的 DeepSeek Harness 捆绑套件。
// 每个 skill 经官方 skills 通道静态注册(读各自 SKILL.md frontmatter);
// 每技能一条斜杠命令给"30 秒路由卡",另加 /suite-status 总览。
// 无原生工具、无引擎调用、无遥测;技能各自的联网行为见 README 安全声明表。
// 契约依据:docs/cordis-tutorial + cookbook/adding-a-tool(命令防御式注册同款)。
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";

const SKILLS_DIR = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)), "..", "skills");

function readFrontmatter(dir) {
  const raw = fs.readFileSync(path.join(dir, "SKILL.md"), "utf8");
  const m = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/.exec(raw);
  const fm = m ? m[1] : "";
  const body = (m ? m[2] : raw).trim();
  const pick = (key) => {
    const line = fm.split(/\r?\n/).find((l) => l.toLowerCase().startsWith(key + ":"));
    return line ? line.slice(key.length + 1).trim() : "";
  };
  return { body, name: pick("name"), description: pick("description"), version: pick("version") };
}

export const name = "dsh-scholar-suite";
export const inject = ["skills", "commands"];

export function apply(ctx) {
  const dirs = fs.readdirSync(SKILLS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory() && fs.existsSync(path.join(SKILLS_DIR, d.name, "SKILL.md")))
    .map((d) => d.name)
    .sort();
  const loaded = [];
  for (const dir of dirs) {
    try {
      const fm = readFrontmatter(path.join(SKILLS_DIR, dir));
      loaded.push({
        dir,
        name: fm.name || dir,
        version: fm.version || "",
        description: fm.description || "",
        body: fm.body,
      });
    } catch (e) {
      // 单个技能损坏不拖垮整包:跳过并告警
      console.warn("[dsh-scholar-suite] 跳过损坏技能:", dir, String(e));
    }
  }

  // ---- 捆绑 Skill(静态注册:官方 SkillRegistration 形状;一个失败不影响其余) ----
  ctx.inject(["skills"], (c) => {
    if (!c.skills || typeof c.skills.register !== "function") return;
    for (const s of loaded) {
      try {
        c.skills.register({
          name: s.name,
          description: s.description || s.name,
          content: s.body,
          metadata: { version: s.version, suite: "dsh-scholar-suite" },
          source: "bundled",
        });
      } catch (e) {
        console.warn("[dsh-scholar-suite] skill 注册失败:", s.name, String(e));
      }
    }
  });

  // ---- 斜杠命令:每技能一条 30 秒路由卡 + 总览(防御式:commands 通道可能缺席) ----
  ctx.inject(["commands"], (c) => {
    if (!c.commands || typeof c.commands.register !== "function") return;
    c.effect(() => {
      const disposers = [];
      const list = loaded.map((s) =>
        `- ${s.name}${s.version ? " v" + s.version : ""}:${(s.description || "").replace(/\s+/g, " ").slice(0, 90)}`
      ).join("\n");
      disposers.push(c.commands.register({
        name: "suite-status",
        description: "列出 dsh-scholar-suite 捆绑的全部技能与版本。",
        input: { hint: "" },
        handler: async () => ({
          kind: "success",
          text: `dsh-scholar-suite · 捆绑 ${loaded.length} 技能:\n${list}\n\n用 /<技能名> 取该技能的方法卡;直接说需求时,模型会按已注册技能自动路由。`,
        }),
      }));
      for (const s of loaded) {
        const cmd = s.dir.toLowerCase().replace(/[^a-z0-9-]/g, "-");
        disposers.push(c.commands.register({
          name: cmd,
          description: "调取 " + s.name + " 的方法卡(能力×边界×入口);可带一句需求。",
          input: { hint: "<需求描述(可选)>" },
          handler: async (invocation) => {
            const ask = (invocation?.rawInput || "").trim();
            const card = s.body.slice(0, 2400) +
              (s.body.length > 2400 ? "\n…(完整内容已注册为技能,按需引用)" : "");
            return {
              kind: "success",
              text: (ask ? `需求「${ask}」→ 按 ${s.name} 的方法处理:\n\n` : "") + card,
            };
          },
        }));
      }
      return () => { for (const d of disposers) { try { d(); } catch {} } };
    });
  });
}
