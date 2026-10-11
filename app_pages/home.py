"""Public, no-model landing page for QuickHealth."""

import re

import streamlit as st


HOME_STYLES = """<style>
      .block-container { max-width: 1120px; padding-top: 1.1rem; }
      .qh-home { color: #1F2D2A; font-family: ui-rounded, "SF Pro Rounded", "Segoe UI", system-ui, sans-serif; line-height: 1.6; }
      .qh-home * { box-sizing: border-box; }
      .qh-home h1, .qh-home h2, .qh-home h3 { color: #0F4C3A; line-height: 1.12; letter-spacing: -.035em; }
      .qh-home h1 { margin: 0 0 1.1rem; font-size: clamp(2.5rem, 6vw, 4.2rem); font-weight: 850; }
      .qh-home h2 { font-size: clamp(1.9rem, 4vw, 2.7rem); }
      .qh-home h3 { font-size: 1.35rem; }
      .qh-top { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding: .5rem 0 1.2rem; border-bottom:1px solid #D8DED8; }
      .qh-brand { display:flex; align-items:center; gap:.55rem; color:#0F4C3A; font-weight:850; font-size:1.25rem; }
      .qh-brand svg { width:38px; height:38px; }
      .qh-nav { display:flex; flex-wrap:wrap; gap:1.2rem; }
      .qh-nav a, .qh-home a { color:#0F4C3A; text-underline-offset:.2em; }
      .qh-hero { display:grid; grid-template-columns:1.08fr .92fr; align-items:center; gap:clamp(1.5rem,5vw,4rem); padding:4rem 0 5rem; }
      .qh-eyebrow { display:inline-block; margin:0 0 1.1rem; padding:.4rem .85rem; border-radius:99px; background:#E4EDE2; color:#0F4C3A; font-size:.85rem; font-weight:800; }
      .qh-copy { max-width:620px; font-size:1.1rem; line-height:1.75; }
      .qh-art { min-height:340px; display:grid; place-items:center; position:relative; isolation:isolate; }
      .qh-shape { position:absolute; border-radius:48% 52% 58% 42% / 50% 43% 57% 50%; }
      .qh-sage { width:88%; height:84%; background:#E4EDE2; transform:rotate(-8deg); }
      .qh-peach { width:65%; height:68%; right:0; top:1%; background:#FADBD0; transform:rotate(13deg); }
      .qh-cream { width:55%; height:58%; left:0; bottom:2%; background:#F3E8D9; transform:rotate(-11deg); }
      .qh-art-card { position:relative; z-index:1; width:min(76%,340px); padding:2rem; border:1px solid #D8DED8; border-radius:30px; background:#FFFBF7; box-shadow:0 18px 45px rgba(15,76,58,.12); text-align:center; color:#0F4C3A; font-weight:800; }
      .qh-art-card svg { width:135px; max-width:100%; height:auto; display:block; margin:auto auto 1rem; }
      .qh-section { padding:3.6rem 0; }
      .qh-center { max-width:700px; margin:0 auto 2rem; text-align:center; }
      .qh-pathways { margin:0 -1rem; padding:3rem 1rem; background:#F7F2EB; }
      .qh-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1.3rem; }
      .qh-card { min-height:270px; padding:clamp(1.5rem,3vw,2.5rem); border-radius:28px; color:#1F2D2A; }
      .qh-card--mother { background:#FADBD0; }
      .qh-card--child { background:#FDEFC7; }
      .qh-icon { width:50px; height:50px; display:grid; place-items:center; margin-bottom:1rem; border-radius:50%; background:#FFFBF7; }
      .qh-icon svg { width:28px; height:28px; }
      .qh-symbol { position:relative; display:block; width:30px; height:30px; color:#0F4C3A; }
      .qh-symbol--pregnancy { font:30px/30px Arial,sans-serif; text-align:center; }
      .qh-symbol--pregnancy::before { content:"♥"; }
      .qh-symbol--child::before { position:absolute; top:2px; left:11px; width:8px; height:8px; border:2px solid #0F4C3A; border-radius:50%; content:""; }
      .qh-symbol--child::after { position:absolute; bottom:2px; left:4px; width:22px; height:13px; border:2px solid #0F4C3A; border-bottom:0; border-radius:14px 14px 0 0; content:""; }
      .qh-symbol--chat { width:22px; height:17px; border:2px solid #0F4C3A; border-radius:3px; }
      .qh-symbol--chat::before { position:absolute; bottom:-6px; left:2px; width:7px; height:7px; border-left:2px solid #0F4C3A; transform:skew(-30deg); content:""; }
      .qh-symbol--chat::after { position:absolute; top:4px; left:4px; width:10px; height:2px; background:#0F4C3A; box-shadow:0 5px #0F4C3A; content:""; }
      .qh-symbol--shield { width:24px; height:28px; background:#0F4C3A; clip-path:polygon(50% 0,100% 16%,94% 63%,50% 100%,6% 63%,0 16%); }
      .qh-symbol--shield::after { position:absolute; top:6px; left:7px; width:8px; height:5px; border-bottom:2px solid white; border-left:2px solid white; transform:rotate(-45deg); content:""; }
      .qh-symbol--document { width:20px; height:26px; border:2px solid #0F4C3A; border-radius:2px; background:linear-gradient(#0F4C3A,#0F4C3A) 4px 8px/10px 2px no-repeat,linear-gradient(#0F4C3A,#0F4C3A) 4px 13px/10px 2px no-repeat,linear-gradient(#0F4C3A,#0F4C3A) 4px 18px/7px 2px no-repeat; }
      .qh-card p { margin-bottom:0; }
      .qh-steps { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1.4rem; text-align:center; }
      .qh-step { padding:1rem .7rem; }
      .qh-step .qh-icon { width:64px; height:64px; margin:0 auto 1rem; background:#E4EDE2; }
      .qh-safety { margin:2rem 0 3rem; padding:clamp(1.7rem,4vw,3rem); border-radius:30px; background:#E4EDE2; }
      .qh-safety ul { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem 2rem; padding-left:1.2rem; }
      .qh-alert { padding:1rem 1.2rem; border-left:5px solid #A83222; border-radius:12px; background:#FFFBF7; font-weight:750; }
      .qh-footer { padding:1.5rem 0; border-top:1px solid #D8DED8; font-size:.92rem; }
      .qh-footer-note { margin-top:.7rem; }
      .qh-nav .qh-demo-link { display:inline-flex; align-items:center; justify-content:center; min-height:56px; padding:.7rem 1.6rem; border:2px solid #0F4C3A; border-radius:999px; background:#0F4C3A; color:#fff; font-size:1.2rem; font-weight:800; text-decoration:none; }
      .qh-nav .qh-demo-link:focus-visible { outline:3px solid #A83222; outline-offset:4px; }
      .st-key-home_demo_hero button, .st-key-home_demo_pathways button { min-height:56px; padding:.7rem 1.6rem; border:2px solid #0F4C3A; border-radius:999px; background:#0F4C3A; color:#fff; font-size:1.2rem; font-weight:800; }
      .st-key-home_demo_hero button:focus-visible, .st-key-home_demo_pathways button:focus-visible { outline:3px solid #A83222; outline-offset:4px; }
      .st-key-home_demo_hero button { min-height:64px; padding-inline:2rem; font-size:1.35rem; }
      @media(max-width:560px) { .qh-nav .qh-demo-link, .st-key-home_demo_hero, .st-key-home_demo_hero button, .st-key-home_demo_pathways, .st-key-home_demo_pathways button { width:100%; } }
      @media(max-width:760px) { .qh-hero { grid-template-columns:1fr; padding:2.7rem 0 3.2rem; } .qh-art { min-height:290px; } .qh-steps { grid-template-columns:1fr; gap:.5rem; } }
      @media(max-width:560px) { .qh-nav { gap:.6rem; font-size:.84rem; } .qh-grid, .qh-safety ul { grid-template-columns:1fr; } .qh-pathways { margin:0 -.6rem; padding-inline:.6rem; } .qh-art { min-height:260px; } }
      @media(prefers-reduced-motion:reduce) { .qh-home *, .qh-home *::before, .qh-home *::after { scroll-behavior:auto !important; transition:none !important; animation:none !important; } }
    </style>"""

def _icons_as_css_shapes(markup):
    def replace_icon(match):
        svg = match.group(1)
        label = re.search(r'aria-label="([^"]*)"', svg)
        description = label.group(1) if label else ""
        if "Pregnancy" in description:
            icon, alt = "pregnancy", "Pregnancy pathway icon"
        elif "Child" in description:
            icon, alt = "child", "Child health pathway icon"
        elif "History" in description:
            icon, alt = "chat", "History questions icon"
        elif "Rules" in description:
            icon, alt = "shield", "Rules check icon"
        else:
            icon, alt = "document", "Structured note icon"
        return f'<span class="qh-symbol qh-symbol--{icon}" role="img" aria-label="{alt}"></span>'

    return re.sub(r'(?<=<span class="qh-icon">)(<svg\b.*?</svg>)(?=</span>)', replace_icon, markup)


st.html(
    _icons_as_css_shapes(HOME_STYLES + """
    <div class="qh-home">
      <header class="qh-top">
        <div class="qh-brand" aria-label="QuickHealth heart and leaf logo">
          <svg viewBox="0 0 48 48" role="img" aria-label="Heart and leaf logo" xmlns="http://www.w3.org/2000/svg"><path d="M24 40S5 29 5 16.8C5 7.2 17.2 4.5 24 14c6.8-9.5 19-6.8 19 2.8C43 29 24 40 24 40Z" fill="none" stroke="#0F4C3A" stroke-width="3.5"/><path d="M20 27c.2-7.2 5.6-12 13-12-1 7.8-5.7 12.1-13 12Z" fill="#0F4C3A"/><path d="M15 32c2.2-3.4 5.4-6.1 9.5-8.4" fill="none" stroke="#0F4C3A" stroke-width="2.4"/></svg>
          QuickHealth
        </div>
        <nav class="qh-nav" aria-label="Home sections"><a href="#home">Home</a><a href="#mothers">For Mothers</a><a href="#children">For Children</a><a href="#about">About</a><a class="qh-demo-link" href="/demo" target="_top">Try the demo</a></nav>
      </header>
      <main>
        <section class="qh-hero" id="home">
          <div><p class="qh-eyebrow">Built for neatHack 2026</p><h1>Faster, safer history-taking for mothers and children.</h1><p class="qh-copy">QuickHealth helps nurses and health workers take a clear clerking history, spot danger signs early, and produce a clinician-ready note.</p></div>
          <div class="qh-art" role="img" aria-label="A calm heart and leaf illustration in cream, peach and sage"><div class="qh-shape qh-sage"></div><div class="qh-shape qh-peach"></div><div class="qh-shape qh-cream"></div><div class="qh-art-card"><svg viewBox="0 0 180 180" aria-label="Heart and leaf illustration" role="img" xmlns="http://www.w3.org/2000/svg"><path d="M90 151S27 113 27 70c0-29 37-40 63-7 26-33 63-22 63 7 0 43-63 81-63 81Z" fill="#FADBD0" stroke="#0F4C3A" stroke-width="5"/><path d="M76 99c1-26 20-43 48-43-3 28-21 44-48 43Z" fill="#0F4C3A"/><path d="M58 116c11-15 26-27 47-38" fill="none" stroke="#0F4C3A" stroke-width="5"/></svg>Clear questions. Careful notes.</div></div>
        </section>
      </main>
    </div>
    """)
)

st.button(
    "Try the demo",
    key="home_demo_hero",
    type="primary",
    on_click=st.switch_page,
    args=("app_pages/demo.py",),
)
st.markdown('[See how it works](#how)')
st.button(
    "Explore a pathway in the demo",
    key="home_demo_pathways",
    on_click=st.switch_page,
    args=("app_pages/demo.py",),
)

st.html(
    _icons_as_css_shapes(HOME_STYLES + """
    <div class="qh-home">
      <section class="qh-pathways" aria-labelledby="pathway-heading"><div class="qh-center"><h2 id="pathway-heading">Support for every stage</h2><p>Focused pathways help gather the details that matter for a clear clinical history.</p></div>
        <div class="qh-grid">
          <article class="qh-card qh-card--mother" id="mothers"><span class="qh-icon"><svg viewBox="0 0 32 32" role="img" aria-label="Pregnancy pathway icon"><path d="M16 27s-9-5.6-9-12.5C7 9.8 12.5 8 16 13c3.5-5 9-3.2 9 1.5C25 21.4 16 27 16 27Z" fill="none" stroke="#0F4C3A" stroke-width="2.3"/><path d="M14 18c.2-3.6 2.7-5.8 6.5-5.8-.5 3.8-2.8 5.8-6.5 5.8Z" fill="#0F4C3A"/></svg></span><h3>Pregnancy and postnatal pathway</h3><p>Asks about gestational age, antenatal care, and danger signs such as severe headache with visual changes, bleeding and reduced fetal movement.</p></article>
          <article class="qh-card qh-card--child" id="children"><span class="qh-icon"><svg viewBox="0 0 32 32" role="img" aria-label="Child health pathway icon"><circle cx="16" cy="11" r="5" fill="none" stroke="#0F4C3A" stroke-width="2.3"/><path d="M6.5 27c.7-6.1 4-9.1 9.5-9.1s8.8 3 9.5 9.1" fill="none" stroke="#0F4C3A" stroke-width="2.3"/></svg></span><h3>Child health pathway</h3><p>History taken from the caregiver, including feeding, immunisation and danger signs in infants and children under five.</p></article>
        </div>
      </section>
      <section class="qh-section" id="how" aria-labelledby="how-heading"><div class="qh-center"><h2 id="how-heading">How it works</h2><p>A guided flow keeps the history focused and makes the next steps clear.</p></div><div class="qh-steps">
        <article class="qh-step"><span class="qh-icon"><svg viewBox="0 0 32 32" role="img" aria-label="History questions icon"><path d="M7 7.5h18v14H15l-6 4v-4H7v-14Z" fill="none" stroke="#0F4C3A" stroke-width="2.2"/><path d="M11 12h10M11 17h7" stroke="#0F4C3A" stroke-width="2.2"/></svg></span><h3>Take the history</h3><p>Adaptive questions, one at a time.</p></article>
        <article class="qh-step"><span class="qh-icon"><svg viewBox="0 0 32 32" role="img" aria-label="Rules check icon"><path d="M16 4 27 8v7c0 7-4.5 11-11 14C9.5 26 5 22 5 15V8l11-4Z" fill="none" stroke="#0F4C3A" stroke-width="2.2"/><path d="m10.5 16 3.5 3.5 7.5-8" fill="none" stroke="#0F4C3A" stroke-width="2.2"/></svg></span><h3>Check for danger signs</h3><p>A rules file, not the AI, decides urgency.</p></article>
        <article class="qh-step"><span class="qh-icon"><svg viewBox="0 0 32 32" role="img" aria-label="Structured note icon"><path d="M9 4.5h10l5 5V27H9V4.5Z" fill="none" stroke="#0F4C3A" stroke-width="2.2"/><path d="M19 4.5v5h5M12.5 15h8M12.5 19.5h8M12.5 24h5" stroke="#0F4C3A" stroke-width="2.2"/></svg></span><h3>Get a clear note</h3><p>A structured clerking note and a plain-language summary for the clinician to review.</p></article>
      </div></section>
      <section class="qh-safety" id="about" aria-labelledby="safety-heading"><h2 id="safety-heading">Built to be careful</h2><ul><li>QuickHealth never diagnoses.</li><li>Urgency is decided by a rules file.</li><li>Completeness and contradiction checks run before a note is finished.</li><li>This prototype uses fictional cases only.</li><li>The rules have not yet been reviewed by a clinician.</li><li>QuickHealth is not medical advice.</li></ul><p class="qh-alert">If someone has danger signs, call emergency services.</p></section>
      <footer class="qh-footer"><p><a href="https://github.com/dynaayowilliams-dot/quickhealth">View the project on GitHub</a></p><p class="qh-footer-note">QuickHealth is not medical advice. If someone has danger signs, call emergency services.</p><p style="margin-top:1.2rem">Built for neatHack 2026 with neatlogs, Entire and cfo.ai<br><span style="font-size:.86em;color:#52635E">Code written with Codex</span></p></footer>
    </div>
    """)
)

