"""
Configuration for the daily law-tech / reg-tech digest.

Everything you'd want to tune lives here so digest.py stays stable.
"""

# ---------------------------------------------------------------------------
# FEEDS
# ---------------------------------------------------------------------------
# Mix of native RSS + Google News RSS queries.
# Google News pattern turns ANY search into a feed - useful for sources
# (PDPC, IMDA, MAS) that don't publish RSS themselves.
FEEDS = [
    # --- Legal tech / legal ops ---
    "https://www.artificiallawyer.com/feed/",
    "https://www.legaltechnology.com/feed/",
    "https://www.lawnext.com/feed/",

    # --- Privacy / AI policy ---
    "https://fpf.org/feed/",
    "https://iapp.org/news/rss",

    # --- Singapore regulators (via Google News, they lack clean RSS) ---
    "https://news.google.com/rss/search?q=(PDPC+OR+IMDA)+(data+protection+OR+%22AI+governance%22)+when:7d&hl=en-SG&gl=SG&ceid=SG:en",
    "https://news.google.com/rss/search?q=MAS+Singapore+(RegTech+OR+%22technology+risk%22+OR+%22AI+governance%22)+when:7d&hl=en-SG&gl=SG&ceid=SG:en",

    # --- Broad sweep ---
    "https://news.google.com/rss/search?q=(%22AI+governance%22+OR+RegTech+OR+%22legal+operations%22+OR+%22EU+AI+Act%22)+when:3d&hl=en-SG&gl=SG&ceid=SG:en",
]

# ---------------------------------------------------------------------------
# SCORING
# ---------------------------------------------------------------------------
# Weighted keywords. Positive = want it. Negative = filter out noise.
# Tune these as you read - if you keep getting junk, add a negative term.
KEYWORDS = {
    # Tier 1: core interest, high signal
    "ai governance":        12,
    "regtech":              12,
    "iso 42001":            12,
    "nist ai rmf":          12,
    "eu ai act":            10,
    "legal operations":     10,
    "responsible ai":        9,
    "algorithmic accountability": 9,

    # Tier 2: strongly relevant
    "pdpa":                  9,
    "dpia":                  9,
    "privilege":             8,
    "data protection":       7,
    "contract lifecycle":    7,
    "legal tech":            7,
    "ai act":                7,
    "model governance":      7,
    "ai risk":               7,

    # Tier 3: contextual
    "compliance":            4,
    "privacy":               4,
    "clm":                   4,
    "law firm":              4,
    "general counsel":       4,
    "in-house legal":        4,
    "automation":            3,

    # Geography boosters (you're Singapore-based)
    "singapore":             6,
    "imda":                  8,
    "pdpc":                  8,
    "mas ":                  5,   # trailing space avoids matching "massive"
    "asean":                 4,

    # Negative: kills the funding/marketing noise that floods legal-tech feeds
    "series a":             -8,
    "series b":             -8,
    "raises $":             -8,
    "funding round":        -7,
    "webinar":              -9,
    "sponsored":           -12,
    "podcast episode":      -5,
    "job opening":         -10,
    "hiring":               -6,
    "discount":            -10,
}

# ---------------------------------------------------------------------------
# TAXONOMY
# ---------------------------------------------------------------------------
# Each article gets tagged against the frameworks you're learning.
# Over months this builds a dataset: which topics actually dominate coverage.
TAXONOMY = {
    "AI GOVERNANCE":  ["ai governance", "responsible ai", "iso 42001",
                       "nist ai rmf", "ai risk", "model governance",
                       "algorithmic accountability"],
    "AI REGULATION":  ["eu ai act", "ai act", "ai bill", "ai regulation",
                       "ai law"],
    "DATA PRIVACY":   ["pdpa", "gdpr", "dpia", "data protection", "privacy",
                       "pdpc", "personal data"],
    "LEGAL OPS":      ["legal operations", "legal ops", "contract lifecycle",
                       "clm", "matter management", "legal spend"],
    "LEGAL TECH":     ["legal tech", "legaltech", "law firm technology",
                       "e-discovery", "document automation"],
    "REGTECH":        ["regtech", "suptech", "compliance technology",
                       "regulatory reporting"],
    "PROF CONDUCT":   ["privilege", "sanction", "hallucinat", "professional conduct",
                       "duty of competence", "confidentiality"],
    "CYBER / RISK":   ["cyber", "iso 27001", "mas trm", "technology risk",
                       "breach", "incident response"],
}

# ---------------------------------------------------------------------------
# BEHAVIOUR
# ---------------------------------------------------------------------------
MIN_SCORE       = 8      # below this, article isn't worth your morning
SEEN_MEMORY     = 800    # how many article IDs to remember (dedup window)
CANDIDATE_POOL  = 8      # top-N passed to the LLM for final pick
HTTP_TIMEOUT    = 20     # seconds per feed
USER_AGENT      = "lawtech-daily/1.0 (personal reading digest)"
