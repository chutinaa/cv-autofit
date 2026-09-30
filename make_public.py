# -*- coding: utf-8 -*-
"""
make_public.py  —  build the publishable cv_studio.html from the private resume_studio.html

  python make_public.py [--src ../resume_studio.html] [--out cv_studio.html]

What it does
  1. Replaces the whole built-in seed data (defaultDocs) with a fictional student
     (Léa Martin / 林晓雨, 4th-year medical student applying for a Research Assistant role).
  2. Simplifies SEED_MAP / defaultState / migration code that referred to private versions.
  3. Uses a separate localStorage key so the public build never collides with the private one.
  4. Asserts that none of the terms listed in private_terms.txt (git-ignored) remain in the output.
"""
import re, json, sys, argparse, io

LAYOUT = {"mv": 18, "mh": 20, "fs": 13, "lh": 1.38, "sg": 18, "eg": 10, "bg": 2, "ph": 22, "ff": ""}

def L():  # fresh copy each time
    return dict(LAYOUT)

EN = {
 "name": "Léa Martin", "tagline": "", "layout": L(),
 "sections": [
  {"title": "Education", "type": "entries", "locked": True, "entries": [
   {"org": "XX University — School of Medicine", "loc": "",
    "role": "MD Programme, 4th year (DFASM1) | Elective track: Clinical Research Methods",
    "dates": "2022 – Present",
    "bullets": ["Core courses: Biostatistics | Epidemiology | Neurology | Internal Medicine | Evidence-Based Medicine | Research Ethics (GCP certified)"]},
   {"org": "XX High School", "loc": "",
    "role": "Baccalauréat Scientifique, mention Très Bien (17.6/20)", "dates": "2019 – 2022", "bullets": []}
  ]},
  {"title": "Research Experience", "type": "entries", "locked": True, "entries": [
   {"org": "XX Neuroscience Institute — Sleep & Cognition Lab", "loc": "",
    "role": "Student Research Assistant (part-time)", "dates": "Sep 2025 – Present",
    "bullets": [
     "Cohort Data Management: Maintained a REDCap database for a 240-participant longitudinal sleep cohort, wrote data-quality rules that flagged 3.1% of entries for review and cut monthly cleaning time from ~2 days to half a day.",
     "Polysomnography Scoring: Scored 180+ overnight PSG recordings under AASM criteria with inter-rater agreement of κ = 0.86 against a senior technician; built a scoring checklist adopted by two new students.",
     "Statistical Analysis: Ran mixed-effects models in R (lme4) linking slow-wave sleep duration to next-day memory scores; results contributed to a poster accepted at a 2026 international sleep research congress."
    ]},
   {"org": "XX University Hospital — Department of Neurology", "loc": "",
    "role": "Clinical Research Intern (summer)", "dates": "Jun – Aug 2025",
    "bullets": [
     "Patient Recruitment: Screened 420 outpatient records for a phase-III stroke rehabilitation trial, pre-identified 61 eligible candidates and supported informed-consent visits with the study coordinator.",
     "Regulatory Documentation: Prepared adverse-event forms and monitoring binders for two sponsor audits with zero major findings; standardized the source-document checklist used across 3 study sites.",
     "Literature Review: Synthesized 45 papers on post-stroke motor recovery into a structured evidence table (PICO format) used in the protocol amendment."
    ]}
  ]},
  {"title": "Clinical Experience", "type": "entries", "locked": True, "entries": [
   {"org": "XX Hospital — Internal Medicine", "loc": "",
    "role": "Clinical Rotation (externe)", "dates": "Jan – Apr 2026",
    "bullets": [
     "Ward Follow-up: Managed 6–8 inpatients daily under supervision, including history taking, physical exams, case presentations at morning rounds and discharge summaries.",
     "Peer Teaching: Led a 15-minute session on anticoagulation reversal for 12 fellow students; rated 4.7/5 in peer feedback."
    ]}
  ]},
  {"title": "Projects & Publications", "type": "entries", "locked": True, "entries": [
   {"org": "Meta-analysis: Melatonin and Delirium Prevention in ICU", "loc": "", "role": "First author, student research project (UE Recherche)", "dates": "Oct 2025 – Mar 2026",
    "bullets": [
     "Screened 1,120 abstracts and 38 full texts following PRISMA; pooled 9 RCTs (n = 1,432) with random-effects models in R (metafor), assessed risk of bias with RoB 2 and heterogeneity with I².",
     "Manuscript under review at a peer-reviewed journal; presented at the faculty research day (2nd prize, student session)."
    ]},
   {"org": "Open-Source Tool: PSG Annotation Helper", "loc": "GitHub", "role": "Python / Streamlit", "dates": "Dec 2025",
    "bullets": ["Built a small web app that visualizes EEG epochs and exports AASM sleep-stage labels to CSV, now used by 4 lab members for pilot scoring."]}
  ]},
  {"title": "Additional Information", "type": "text", "locked": True, "lines": [
   "Languages: French (Native) | English (C1, IELTS 8.0) | Spanish (B1)",
   "Technical Skills: R (tidyverse, lme4, metafor) | Python (pandas, MNE) | SPSS | REDCap | Zotero | LaTeX",
   "Certifications: Good Clinical Practice (ICH-GCP, 2025) | Basic Life Support (2024)",
   "Interests: Long-distance running (half-marathon 2025) | Science outreach volunteer"
  ]}
 ],
 "contacts": [
  {"text": "+33 6 00 00 00 00", "url": ""},
  {"text": "lea.martin@example.com", "url": ""},
  {"text": "LinkedIn", "url": "https://www.linkedin.com/in/example"},
  {"text": "ORCID", "url": "https://orcid.org/0000-0000-0000-0000"}
 ]
}

CN = {
 "name": "林晓雨", "tagline": "", "layout": L(),
 "sections": [
  {"title": "教育背景", "type": "entries", "locked": True, "entries": [
   {"org": "XX大学医学院", "loc": "", "role": "临床医学（五年制）本科四年级", "dates": "2022.09 – 2027.06",
    "bullets": ["【学业成绩】GPA 3.82/4.0（专业前5%），获国家奖学金、校优秀学生", "【核心课程】医学统计学、流行病学、神经病学、内科学、循证医学、医学科研方法"]}
  ]},
  {"title": "科研经历", "type": "entries", "locked": True, "entries": [
   {"org": "XX大学脑科学研究院 睡眠与认知实验室", "loc": "", "role": "本科生科研助理（兼职）", "dates": "2025.09 – 至今",
    "bullets": [
     "【队列数据管理】负责240人睡眠纵向队列的REDCap数据库维护，编写数据质控规则自动标记3.1%的异常录入，月度清洗时间由约2天缩短至半天。",
     "【多导睡眠图判读】按AASM标准完成180+份整夜PSG分期，与高年资技师的一致性κ=0.86；整理判读清单被两名新进学生沿用。",
     "【统计分析】使用R（lme4）建立混合效应模型，分析慢波睡眠时长与次日记忆成绩的关联，结果纳入2026年一场国际睡眠研究会议海报。"
    ]},
   {"org": "XX医院神经内科", "loc": "", "role": "临床研究暑期实习生", "dates": "2025.06 – 2025.08",
    "bullets": [
     "【受试者招募】筛查420份门诊病历，为一项卒中康复III期临床试验预筛61名符合入组条件的候选者，协助研究协调员完成知情同意访视。",
     "【研究文书与稽查】整理不良事件表与监查文件夹，配合两次申办方稽查零重大发现；统一3家分中心的源文件核对清单。",
     "【文献综述】按PICO框架梳理45篇卒中后运动功能恢复文献，形成证据表并用于方案修订。"
    ]}
  ]},
  {"title": "临床经历", "type": "entries", "locked": True, "entries": [
   {"org": "XX医院内科", "loc": "", "role": "临床见习", "dates": "2026.01 – 2026.04",
    "bullets": [
     "【病房随访】在带教指导下负责6–8名住院患者的日常管理，包括问诊查体、晨间交班病例汇报与出院小结撰写。",
     "【教学分享】面向12名同学开展15分钟抗凝逆转专题小讲课，同伴评分4.7/5。"
    ]}
  ]},
  {"title": "项目与成果", "type": "entries", "locked": True, "entries": [
   {"org": "褪黑素预防ICU谵妄的Meta分析", "loc": "", "role": "第一作者 · 本科生科研项目", "dates": "2025.10 – 2026.03",
    "bullets": [
     "【系统检索与合并】按PRISMA流程筛选1120篇摘要、38篇全文，纳入9项RCT（n=1432），使用R（metafor）随机效应模型合并，RoB 2评估偏倚风险、I²评估异质性。",
     "【成果】论文已投稿同行评审期刊；在学院科研日汇报并获学生组二等奖。"
    ]},
   {"org": "开源工具：PSG标注助手", "loc": "GitHub", "role": "Python / Streamlit", "dates": "2025.12",
    "bullets": ["搭建轻量网页工具，可视化EEG片段并导出AASM睡眠分期标签为CSV，目前实验室4名成员用于预判读。"]}
  ]},
  {"title": "技能与其他", "type": "text", "locked": True, "lines": [
   "语言：中文（母语）、英语（雅思8.0，可作为工作语言）、法语（A2）",
   "技能：R（tidyverse、lme4、metafor）、Python（pandas、MNE）、SPSS、REDCap、Zotero、LaTeX",
   "证书：ICH-GCP临床试验质量管理规范（2025）、基础生命支持BLS（2024）",
   "其他：半程马拉松完赛（2025）、科技馆科普志愿者"
  ]}
 ],
 "contacts": [
  {"text": "138 0000 0000", "url": ""},
  {"text": "linxiaoyu@example.com", "url": ""},
  {"text": "ORCID", "url": "https://orcid.org/0000-0000-0000-0000"}
 ]
}

FR = {
 "name": "Léa Martin", "tagline": "Étudiante en médecine (DFASM1) — recherche un poste d'assistante de recherche clinique", "layout": L(),
 "sections": [
  {"title": "Formation", "type": "entries", "locked": True, "entries": [
   {"org": "Université XX — Faculté de médecine", "loc": "",
    "role": "Études de médecine, 4e année (DFASM1) | Parcours recherche : méthodes en recherche clinique", "dates": "2022 – aujourd'hui",
    "bullets": ["Cours principaux : Biostatistiques | Épidémiologie | Neurologie | Médecine interne | Médecine fondée sur les preuves | Éthique de la recherche (certification BPC)"]},
   {"org": "Lycée XX", "loc": "", "role": "Baccalauréat scientifique, mention Très Bien (17,6/20)", "dates": "2019 – 2022", "bullets": []}
  ]},
  {"title": "Expérience en recherche", "type": "entries", "locked": True, "entries": [
   {"org": "Institut XX de neurosciences — Laboratoire Sommeil & Cognition", "loc": "", "role": "Assistante de recherche étudiante (temps partiel)", "dates": "Sept. 2025 – aujourd'hui",
    "bullets": [
     "Gestion des données de cohorte : maintenance d'une base REDCap pour une cohorte longitudinale de 240 participants ; rédaction de règles de contrôle qualité signalant 3,1 % des saisies, temps de nettoyage mensuel réduit de 2 jours à une demi-journée.",
     "Lecture de polysomnographies : scoring de plus de 180 enregistrements selon les critères AASM, concordance inter-juges κ = 0,86 avec une technicienne senior ; check-list de scoring reprise par deux nouveaux étudiants.",
     "Analyses statistiques : modèles mixtes sous R (lme4) reliant la durée de sommeil lent profond aux scores de mémoire du lendemain ; résultats intégrés à un poster accepté à un congrès international sur le sommeil (2026)."
    ]},
   {"org": "CHU XX — Service de neurologie", "loc": "", "role": "Stagiaire en recherche clinique (été)", "dates": "Juin – août 2025",
    "bullets": [
     "Recrutement : criblage de 420 dossiers de consultation pour un essai de phase III en rééducation post-AVC, pré-identification de 61 patients éligibles, participation aux visites de consentement.",
     "Documentation réglementaire : préparation des fiches d'événements indésirables et des classeurs de monitoring pour deux audits promoteur sans écart majeur ; harmonisation de la check-list des documents source sur 3 centres.",
     "Revue de littérature : synthèse de 45 articles sur la récupération motrice post-AVC sous forme de tableau de preuves (format PICO) utilisé dans l'amendement du protocole."
    ]}
  ]},
  {"title": "Expérience clinique", "type": "entries", "locked": True, "entries": [
   {"org": "Hôpital XX — Médecine interne", "loc": "", "role": "Stage hospitalier (externe)", "dates": "Janv. – avr. 2026",
    "bullets": [
     "Suivi de patients : prise en charge quotidienne de 6 à 8 patients hospitalisés sous supervision (interrogatoire, examen clinique, présentation des cas au staff, comptes rendus de sortie).",
     "Enseignement : animation d'un topo de 15 minutes sur l'antagonisation des anticoagulants devant 12 étudiants (note de 4,7/5)."
    ]}
  ]},
  {"title": "Projets et publications", "type": "entries", "locked": True, "entries": [
   {"org": "Méta-analyse : mélatonine et prévention du délirium en réanimation", "loc": "", "role": "Première auteure · projet de recherche (UE Recherche)", "dates": "Oct. 2025 – mars 2026",
    "bullets": [
     "Sélection de 1 120 résumés et 38 articles complets selon PRISMA ; 9 essais randomisés inclus (n = 1 432), modèle à effets aléatoires sous R (metafor), risque de biais évalué avec RoB 2, hétérogénéité par I².",
     "Manuscrit en cours de révision dans une revue à comité de lecture ; présentation à la journée recherche de la faculté (2e prix, session étudiante)."
    ]},
   {"org": "Outil open source : PSG Annotation Helper", "loc": "GitHub", "role": "Python / Streamlit", "dates": "Déc. 2025",
    "bullets": ["Application web légère pour visualiser les époques EEG et exporter les stades de sommeil AASM en CSV, utilisée par 4 membres du laboratoire."]}
  ]},
  {"title": "Informations complémentaires", "type": "text", "locked": True, "lines": [
   "Langues : Français (langue maternelle) | Anglais (C1, IELTS 8.0) | Espagnol (B1)",
   "Compétences techniques : R (tidyverse, lme4, metafor) | Python (pandas, MNE) | SPSS | REDCap | Zotero | LaTeX",
   "Certifications : Bonnes pratiques cliniques (ICH-GCP, 2025) | Premiers secours PSC1 (2024)",
   "Centres d'intérêt : Course de fond (semi-marathon 2025) | Bénévolat en médiation scientifique"
  ]}
 ],
 "contacts": [
  {"text": "+33 6 00 00 00 00", "url": ""},
  {"text": "lea.martin@example.com", "url": ""},
  {"text": "LinkedIn", "url": "https://www.linkedin.com/in/example"},
  {"text": "ORCID", "url": "https://orcid.org/0000-0000-0000-0000"}
 ]
}

# identifiers that must never appear in the public build (author's real data).
# Kept OUTSIDE the repo: one term per line in private_terms.txt (git-ignored).
import os
_pt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "private_terms.txt")
FORBIDDEN = [l.strip() for l in io.open(_pt, encoding="utf-8")] if os.path.exists(_pt) else []
FORBIDDEN = [t for t in FORBIDDEN if t and not t.startswith("#")]

def build(src, out):
    html = io.open(src, encoding="utf-8").read()
    n0 = len(html)

    # 1. swap the seed data block
    m = re.search(r"function defaultDocs\(\)\{\s*return \{.*?\n\};\n\}\n", html, re.S)
    assert m, "defaultDocs block not found"
    docs = {"en_ra": EN, "cn_ra": CN, "fr_ra": FR}
    block = "function defaultDocs(){\n return " + json.dumps(docs, ensure_ascii=False, indent=1) + ";\n}\n"
    html = html[:m.start()] + block + html[m.end():]

    # 2. seed map + default state
    html, k = re.subn(r'var SEED_VER="[^"]*",SEED_MAP=\{[^\n]*\};',
        'var SEED_VER="public1",SEED_MAP={en:{"RA":"en_ra"},cn:{"默认":"cn_ra"},fr:{"RA":"fr_ra"}};', html); assert k == 1, "SEED_MAP"
    html, k = re.subn(r'docs:\{en:\{active:"AI",versions:\{"AI":d\.en_ai,"Data":d\.en_analyste\}\},\n\s*cn:\{active:"默认",versions:\{"默认":d\.cn\}\},\n\s*fr:\{active:"AI",versions:\{"AI":d\.fr_ai,"Data":d\.fr_data\}\}\}\};',
        'docs:{en:{active:"RA",versions:{"RA":d.en_ra}},\n          cn:{active:"默认",versions:{"默认":d.cn_ra}},\n          fr:{active:"RA",versions:{"RA":d.fr_ra}}}};', html); assert k == 1, "defaultState"
    html, k = re.subn(r'presets:\{en:"fin",cn:"cn",fr:"fr"\}', 'presets:{en:"en0",cn:"cn0",fr:"fr0"}', html); assert k == 1, "presets"

    # 3. drop private-data migrations (old key + AI/Data/Analyste version renames)
    html, k = re.subn(r'if\(!state\)\{try\{var old=JSON\.parse\(localStorage\.getItem\("resumeStudio_v2"\)\);.*?\n', '', html); assert k == 1, "old-key migration"
    html, k = re.subn(r'  var en=state\.docs\.en;if\(en\.versions\["Analyste"\].*?\n  var fr=state\.docs\.fr,dd=defaultDocs\(\);\n  if\(!fr\.versions\["AI"\].*?\n',
        '  var dd=defaultDocs();\n', html, flags=re.S); assert k == 1, "version migration"

    # 4. separate localStorage key
    html, k = re.subn(r'var LS_KEY="resumeStudio_v3";', 'var LS_KEY="cvStudio_public_v1";', html); assert k == 1, "LS_KEY"

    # 5. leak check
    if not FORBIDDEN:
        print("WARN  private_terms.txt not found, leak check skipped")
    leaks = [w for w in FORBIDDEN if w in html]
    assert not leaks, "private terms still present: %r" % leaks

    io.open(out, "w", encoding="utf-8", newline="").write(html)
    print("OK  %s  %d -> %d bytes" % (out, n0, len(html)))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="../resume_studio.html")
    ap.add_argument("--out", default="cv_studio.html")
    a = ap.parse_args()
    build(a.src, a.out)
