import { useState } from "react";

// ═══════════════════════════════════════════════
// WA-PSS v3.0 — Inclusive Scoring Engine
// © Dr. Rohan J. Kosambiya, 2026
// Scale: CC BY-NC 4.0 | Algorithm: Commercial
// ═══════════════════════════════════════════════

const PSS = [
  { id:"SQ1", t:"Been upset because of unexpected changes in your health parameters on your smartwatch?", r:false, f:1 },
  { id:"SQ2", t:"Felt unable to control important health metrics in your life?", r:false, f:1 },
  { id:"SQ3", t:"Felt nervous and stressed about your health data?", r:false, f:1 },
  { id:"SQ4", t:"Felt confident about handling health problems based on smartwatch data?", r:true, f:2 },
  { id:"SQ5", t:"Felt things were going your way in managing health goals through your device?", r:true, f:2 },
  { id:"SQ6", t:"Found that you could not cope with all the health-related demands and alerts?", r:false, f:1 },
  { id:"SQ7", t:"Been able to control irritations triggered by health monitoring alerts?", r:true, f:3 },
  { id:"SQ8", t:"Felt that you were on top of your health monitoring goals?", r:true, f:3 },
  { id:"SQ9", t:"Been angered because of health metrics that were outside of your control?", r:false, f:1 },
  { id:"SQ10", t:"Felt that health goals and concerns were piling up so high that you could not manage them?", r:false, f:1 },
];

const OPT = ["Never", "Almost Never", "Sometimes", "Fairly Often", "Very Often"];
const REV = new Set([3,4,6,7]);

const GENDERS = [
  { v:"man", l:"Man" },
  { v:"woman", l:"Woman" },
  { v:"non_binary", l:"Non-binary" },
  { v:"genderqueer", l:"Genderqueer" },
  { v:"genderfluid", l:"Genderfluid" },
  { v:"agender", l:"Agender" },
  { v:"two_spirit", l:"Two-Spirit" },
  { v:"prefer_not", l:"Prefer not to say" },
  { v:"self_describe", l:"I describe myself as..." },
];

const BIO_SEX = [
  { v:"afab", l:"Assigned female at birth" },
  { v:"amab", l:"Assigned male at birth" },
  { v:"intersex", l:"Intersex" },
  { v:"prefer_not", l:"Prefer not to say" },
];

const DESIG = ["UG Student","Intern","MBBS / GP","PG Resident","MD / MS","DM / MCh","Nurse","Paramedic","Allied Health","Other"];

const DURATIONS = [{v:0,l:"< 1 week"},{v:1,l:"Weeks"},{v:3,l:"Months"},{v:8,l:"< 1 year"},{v:18,l:"> 1 year"}];

const BRANDS = [
  {v:"apple_watch",l:"Apple Watch"},{v:"coros",l:"COROS"},{v:"garmin",l:"Garmin"},
  {v:"fitbit",l:"Fitbit / Pixel"},{v:"samsung",l:"Samsung"},{v:"polar",l:"Polar"},
  {v:"noise",l:"Noise"},{v:"boat",l:"boAt"},{v:"fireboltt",l:"Fire-Boltt"},{v:"other",l:"Other"},
];

const BIOFIELDS = [
  { k:"heart_rate", l:"Resting Heart Rate", u:"bpm", p:"72", ic:"♥" },
  { k:"hrv", l:"HRV (RMSSD)", u:"ms", p:"45", ic:"∿" },
  { k:"steps", l:"Daily Steps (avg)", u:"steps", p:"8500", ic:"⏦" },
  { k:"sleep_hours", l:"Sleep Duration", u:"hrs", p:"6.5", ic:"◑" },
  { k:"sleep_score", l:"Sleep Score", u:"/100", p:"72", ic:"◐" },
  { k:"spo2", l:"SpO₂", u:"%", p:"97", ic:"◎" },
  { k:"resp_rate", l:"Respiratory Rate", u:"/min", p:"16", ic:"≋" },
  { k:"stress_score", l:"Device Stress", u:"/100", p:"42", ic:"⧫" },
  { k:"active_min", l:"Active Minutes", u:"min", p:"35", ic:"△" },
];

const LOAD = [
  [.64,0,0],[.73,0,0],[.72,0,0],[0,.88,0],[0,.81,0],
  [.87,0,0],[0,0,.66],[0,.36,.66],[.82,0,0],[.76,0,0]
];
const CENT = {
  low_stress_casual:[-.52,-.15,-.30],
  proactive_balanced:[.10,.82,.65],
  high_stress_overmonitor:[.95,-.45,-.25]
};
const MU=[2.1,1.8,1.9], SD=[.85,.90,.80];

const PH = {
  low_stress_casual:{l:"Low-Stress Casual User",c:"#10b981",bg:"#052e16",r:"LOW",
    d:"Minimal distress, low device engagement. Encourage meaningful tracking adoption.",
    rx:["Gamified wellness challenges","Preventive health nudges","Tracking adoption support"]},
  proactive_balanced:{l:"Proactive Balanced User",c:"#0ea5e9",bg:"#0c1d3a",r:"NOMINAL",
    d:"High confidence + emotional regulation + active engagement. Ideal wellness profile.",
    rx:["Advanced coaching integration","Goal escalation features","Peer mentoring candidate"]},
  high_stress_overmonitor:{l:"High-Stress Over-Monitor",c:"#ef4444",bg:"#2d0a0a",r:"HIGH",
    d:"Elevated emotional distress with compulsive monitoring. Immediate intervention indicated.",
    rx:["Tele-MANAS referral (14416)","CBT-based alert modulation","Monitoring frequency caps","Clinician review"]},
  unclassified:{l:"Unclassified",c:"#71717a",bg:"#1a1a1e",r:"INDETERMINATE",
    d:"Ambiguous profile. Additional assessment recommended.",
    rx:["Retest in 2 weeks","Clinical interview recommended"]},
};

function eucl(a,b){return Math.sqrt(a.reduce((s,v,i)=>s+(v-b[i])**2,0))}

function compute(resp, profile, wearable, addl) {
  const sc = resp.map((v,i) => REV.has(i) ? 4-v : v);
  const total = sc.reduce((a,b) => a+b, 0);
  const sev = total<=13 ? "low" : total<=26 ? "moderate" : "high";
  const helpless = [0,1,2,5,8,9].reduce((s,i) => s+sc[i], 0);
  const efficacy = [3,4,6,7].reduce((s,i) => s+sc[i], 0);

  const fRaw = [0,1,2].map(f => {
    const w = LOAD.map(r => r[f]);
    const m = w.map((wt,i) => wt>0?i:-1).filter(i=>i>=0);
    if(!m.length) return 0;
    return m.reduce((s,i) => s+sc[i]*w[i], 0) / m.reduce((s,i) => s+w[i], 0);
  });
  const z = fRaw.map((v,i) => (v-MU[i])/SD[i]);

  const dists = Object.values(CENT).map(c => eucl(z,c));
  const neg = dists.map(d => -d);
  const mx = Math.max(...neg);
  const e = neg.map(v => Math.exp(v-mx));
  const sm = e.reduce((a,b) => a+b, 0);
  const probs = e.map(v => v/sm);
  const keys = Object.keys(CENT);
  const mi = probs.indexOf(Math.max(...probs));
  const conf = probs[mi];
  const pheno = conf >= 0.55 ? keys[mi] : "unclassified";

  const ed = z[0]>1.5, le = z[1]<-1.0;
  const adapt = profile.duration !== null && profile.duration <= 3;
  const tele = sev==="high" || (ed && le);
  const afabRisk = profile.bioSex==="afab" && ed;

  const genderDisplay = profile.gender === "self_describe"
    ? profile.genderCustom
    : GENDERS.find(g => g.v === profile.gender)?.l || profile.gender;

  const wData = Object.fromEntries(
    Object.entries(wearable).filter(([_,v]) => v !== "").map(([k,v]) => [k, parseFloat(v)])
  );

  const itemCount = 10 + (addl[0]!==null?1:0) + (profile.menstruates && addl[1]!==null?1:0);

  const payload = {
    meta: { version:"3.0.0", schema:"wa-pss-temporal-os-v3", timestamp: new Date().toISOString(),
      instrument:"WA-PSS (Wearable-Adapted Perceived Stress Scale)",
      citation:"Kosambiya RJ et al. Indian Journal of Psychological Medicine. 2026.",
      license:{ scale:"CC BY-NC 4.0", algorithm:"Commercial — rjkosambiya@gmail.com" }},
    respondent: {
      gender_identity: profile.gender, gender_display: genderDisplay,
      biological_sex: profile.bioSex || null, menstruates: profile.menstruates,
      age: profile.age ? +profile.age : null, designation: profile.desig, city: profile.city || null,
      items_administered: itemCount,
      wearable: { brand: profile.brand, duration_months: profile.duration }},
    biometrics: wData,
    scoring: { pss_total: total, severity: sev,
      subscales: { perceived_helplessness: { score: helpless, max: 24 }, perceived_self_efficacy: { score: efficacy, max: 16 }},
      additional: { sq11_device_trust: addl[0], ...(profile.menstruates ? { sq12_menstrual_concern: addl[1] } : {})}},
    factor_analysis: { method:"EFA (PAF, Varimax)", variance:"60.2%",
      factors: { emotional_distress:{z:+z[0].toFixed(4)}, self_efficacy:{z:+z[1].toFixed(4)}, emotional_control:{z:+z[2].toFixed(4)} }},
    classification: { phenotype:pheno, label:PH[pheno].l, confidence:+conf.toFixed(4), risk:PH[pheno].r,
      probabilities: Object.fromEntries(keys.map((k,i) => [k, +probs[i].toFixed(4)])) },
    clinical_flags: { elevated_distress:ed, low_self_efficacy:le, afab_elevated_distress:afabRisk,
      adaptation_phase:adapt, tele_manas_referral:tele, tele_manas_helpline: tele?"14416":null },
    interventions: PH[pheno].rx,
    temporal_os: { layer:1, module:"digital_phenotyping", phenotype_id:pheno,
      factor_vector: z.map(s => +s.toFixed(4)), integration_ready:true },
  };

  return { total, sev, helpless, efficacy, z, pheno, conf,
    probs: Object.fromEntries(keys.map((k,i) => [k, probs[i]])),
    tele, ed, le, adapt, afabRisk, genderDisplay, payload };
}

// ── STYLES ──
const C = {
  bg:"#04080f", card:"#0a1122", brd:"#141e33", acc:"#0ea5e9", accD:"#0c4a6e",
  txt:"#e2e8f0", mid:"#94a3b8", dim:"#475569", red:"#ef4444", grn:"#10b981", amb:"#f59e0b",
  pink:"#ec4899", pinkD:"#831843",
  mono:"'JetBrains Mono','Fira Code','Menlo',monospace",
  ui:"'Outfit','Segoe UI',system-ui,sans-serif",
};

const Card = ({children, glow, style}) => (
  <div style={{background:C.card, border:`1px solid ${C.brd}`, borderRadius:14,
    padding:16, marginBottom:12, boxShadow:glow?`0 0 40px ${glow}`:"none",
    transition:"all 0.3s", ...style}}>{children}</div>
);
const Label = ({children}) => (
  <div style={{fontSize:9, fontFamily:C.mono, color:C.accD, textTransform:"uppercase",
    letterSpacing:2.5, marginBottom:10}}>{children}</div>
);
const Btn = ({children, onClick, disabled, v="primary", style:s}) => {
  const vs = {
    primary:{bg:C.accD,c:"#e0f2fe",b:C.acc},
    secondary:{bg:"#1e293b",c:C.mid,b:"#334155"},
    ghost:{bg:"transparent",c:C.dim,b:"#1e293b"}
  };
  const t = vs[v];
  return <button onClick={onClick} disabled={disabled} style={{
    padding:"12px 20px", fontSize:13, fontWeight:700, fontFamily:C.ui,
    background:disabled?"#1e293b":t.bg, color:disabled?"#475569":t.c,
    border:`1px solid ${disabled?"#1e293b":t.b}`, borderRadius:10,
    cursor:disabled?"not-allowed":"pointer", width:"100%", transition:"all 0.2s", ...s
  }}>{children}</button>;
};
const Pill = ({active, children, onClick, color}) => (
  <button onClick={onClick} style={{
    padding:"8px 12px", fontSize:10, fontFamily:C.mono,
    background:active?(color||C.accD):"#111827",
    color:active?"#f0f9ff":C.dim,
    border:`1px solid ${active?(color||C.acc)+"55":"#1e293b"}`,
    borderRadius:8, cursor:"pointer", fontWeight:active?700:400,
    transition:"all 0.15s", whiteSpace:"nowrap", lineHeight:1.3,
  }}>{children}</button>
);
const MiniBar = ({v, max, color}) => (
  <div style={{height:4, background:"#1e293b", borderRadius:2, overflow:"hidden", flex:1}}>
    <div style={{height:"100%", width:`${Math.min(100,(v/max)*100)}%`, background:color,
      borderRadius:2, transition:"width 0.5s"}}/></div>
);

// ── MAIN ──
export default function WAPSSv3() {
  const [tab, setTab] = useState(0);
  const [profile, setP] = useState({
    gender:null, genderCustom:"", bioSex:null, menstruates:null,
    age:"", desig:null, city:"", brand:null, duration:null
  });
  const [wearable, setW] = useState(Object.fromEntries(BIOFIELDS.map(f=>[f.k,""])));
  const [resp, setResp] = useState(Array(10).fill(null));
  const [addl, setAddl] = useState([null, null]); // [sq11, sq12]
  const [result, setResult] = useState(null);
  const [copied, setCopied] = useState(false);

  const answered = resp.filter(r=>r!==null).length;
  const allDone = answered === 10;
  const profileReady = profile.gender !== null && profile.menstruates !== null;

  const doScore = () => { setResult(compute(resp, profile, wearable, addl)); setTab(3); };
  const copyJSON = () => {
    if(result) {
      navigator.clipboard.writeText(JSON.stringify(result.payload,null,2))
        .then(() => { setCopied(true); setTimeout(()=>setCopied(false),2000); });
    }
  };
  const reset = () => {
    setP({gender:null,genderCustom:"",bioSex:null,menstruates:null,age:"",desig:null,city:"",brand:null,duration:null});
    setW(Object.fromEntries(BIOFIELDS.map(f=>[f.k,""])));
    setResp(Array(10).fill(null)); setAddl([null,null]); setResult(null); setTab(0);
  };

  const TABS = [{l:"Profile",ic:"◩"},{l:"Device",ic:"⊛"},{l:"WA-PSS",ic:"◧"},{l:"Results",ic:"◈"},{l:"API",ic:"⟨/⟩"}];
  const sevC = {low:C.grn, moderate:C.amb, high:C.red};

  return (
    <div style={{minHeight:"100vh", background:C.bg, fontFamily:C.ui, color:C.txt,
      maxWidth:520, margin:"0 auto", paddingBottom:80}}>

      {/* HEADER */}
      <div style={{padding:"14px 16px 10px", borderBottom:`1px solid ${C.brd}`,
        background:"linear-gradient(180deg,#0a1122,#04080f)", position:"sticky", top:0, zIndex:100}}>
        <div style={{display:"flex", alignItems:"center", justifyContent:"space-between"}}>
          <div>
            <div style={{fontSize:8, fontFamily:C.mono, letterSpacing:3, color:C.accD, textTransform:"uppercase"}}>Temporal OS · Layer 1</div>
            <div style={{fontSize:18, fontWeight:800, letterSpacing:-0.5}}>WA-PSS<span style={{fontSize:11,fontWeight:400,color:C.dim,marginLeft:6}}>v3.0</span></div>
          </div>
          {profileReady && <div style={{padding:"3px 10px", borderRadius:6, fontSize:9, fontFamily:C.mono,
            background:profile.menstruates?C.pinkD+"88":"#1e293b",
            color:profile.menstruates?C.pink:C.dim,
            border:`1px solid ${profile.menstruates?C.pink+"33":C.brd}`}}>
            {profile.menstruates ? "SQ1–12" : "SQ1–11"}
          </div>}
        </div>
        <div style={{display:"flex", gap:2, marginTop:10}}>
          {TABS.map((t,i) => {
            const active = tab===i;
            const dis = (i===3||i===4) && !result;
            const blocked = i>0 && !profileReady;
            return <button key={i} onClick={()=>!dis&&!blocked&&setTab(i)} style={{
              flex:1, padding:"7px 4px", fontSize:8, fontFamily:C.mono,
              background:active?C.accD:"transparent", color:active?"#e0f2fe":dis||blocked?"#0f172a":C.dim,
              border:`1px solid ${active?C.acc+"44":"transparent"}`, borderRadius:8,
              cursor:dis||blocked?"default":"pointer", opacity:dis||blocked?0.25:1,
              transition:"all 0.2s", letterSpacing:0.5
            }}>
              <span style={{fontSize:11, display:"block", marginBottom:2}}>{t.ic}</span>{t.l}
            </button>;
          })}
        </div>
      </div>

      <div style={{padding:"16px 16px 0"}}>

        {/* ═══ TAB 0: INCLUSIVE PROFILE ═══ */}
        {tab===0 && (<div>
          <Label>Respondent Profile</Label>

          {/* Gender Identity */}
          <Card style={{borderColor:!profile.gender?C.amb+"33":C.acc+"22"}}>
            <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10}}>
              <span style={{fontSize:12, fontWeight:700, color:C.mid}}>Gender Identity <span style={{color:C.red}}>*</span></span>
              {!profile.gender && <span style={{fontSize:8, fontFamily:C.mono, color:C.amb, padding:"2px 6px", background:"#422006", borderRadius:4}}>REQUIRED</span>}
            </div>
            <div style={{display:"flex", flexWrap:"wrap", gap:6}}>
              {GENDERS.map(g => <Pill key={g.v} active={profile.gender===g.v}
                onClick={()=>setP({...profile, gender:g.v})}>{g.l}</Pill>)}
            </div>
            {profile.gender==="self_describe" && (
              <input type="text" value={profile.genderCustom}
                onChange={e=>setP({...profile, genderCustom:e.target.value})}
                placeholder="How do you describe your gender?"
                style={{width:"100%", marginTop:10, padding:"10px 12px", fontSize:13,
                  fontFamily:C.ui, color:C.txt, background:"#111827",
                  border:`1px solid ${profile.genderCustom?C.acc+"33":"#1e293b"}`,
                  borderRadius:8, outline:"none", boxSizing:"border-box"}}/>
            )}
          </Card>

          {/* Biological Sex */}
          <Card>
            <div style={{fontSize:12, fontWeight:700, color:C.mid, marginBottom:4}}>Biological Sex (optional)</div>
            <div style={{fontSize:10, color:C.dim, marginBottom:10, lineHeight:1.5}}>
              Sex assigned at birth. Used only when clinically relevant (e.g., pharmacogenomic dosing).
            </div>
            <div style={{display:"flex", flexWrap:"wrap", gap:6}}>
              {BIO_SEX.map(s => <Pill key={s.v} active={profile.bioSex===s.v}
                onClick={()=>setP({...profile, bioSex:profile.bioSex===s.v?null:s.v})}>{s.l}</Pill>)}
            </div>
          </Card>

          {/* Menstruation — THE KEY QUESTION */}
          <Card style={{borderColor:profile.menstruates===null?C.amb+"33":profile.menstruates?C.pink+"22":C.acc+"22"}}>
            <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:4}}>
              <span style={{fontSize:12, fontWeight:700, color:C.mid}}>Do you currently menstruate? <span style={{color:C.red}}>*</span></span>
              {profile.menstruates===null && <span style={{fontSize:8, fontFamily:C.mono, color:C.amb, padding:"2px 6px", background:"#422006", borderRadius:4}}>REQUIRED</span>}
            </div>
            <div style={{fontSize:10, color:C.dim, marginBottom:10, lineHeight:1.5}}>
              This determines whether the menstrual tracking item (SQ12) is included. This question is independent of gender identity.
            </div>
            <div style={{display:"flex", gap:8}}>
              <Pill active={profile.menstruates===true} color={C.pinkD}
                onClick={()=>setP({...profile, menstruates:true})}>Yes, I menstruate</Pill>
              <Pill active={profile.menstruates===false}
                onClick={()=>setP({...profile, menstruates:false})}>No</Pill>
            </div>
            {profile.menstruates===true && (
              <div style={{marginTop:10, padding:"8px 12px", background:C.pinkD+"22", borderRadius:8,
                fontSize:10, color:C.pink, border:`1px solid ${C.pink}22`}}>
                SQ12 (menstrual tracking concern) will be included in your assessment
              </div>
            )}
            {profile.menstruates===false && (
              <div style={{marginTop:10, padding:"8px 12px", background:C.accD+"22", borderRadius:8,
                fontSize:10, color:C.acc, border:`1px solid ${C.acc}22`}}>
                Assessment: SQ1–SQ11 (11 items)
              </div>
            )}
          </Card>

          {/* Age */}
          <Card>
            <div style={{fontSize:12, fontWeight:700, color:C.mid, marginBottom:8}}>Age</div>
            <input type="number" min={18} max={65} value={profile.age}
              onChange={e=>setP({...profile, age:e.target.value})} placeholder="e.g. 28"
              style={{width:"100%", padding:"10px 12px", fontSize:20, fontFamily:C.mono,
                fontWeight:700, color:C.txt, background:"#111827",
                border:`1px solid ${profile.age?C.acc+"33":"#1e293b"}`,
                borderRadius:8, outline:"none", boxSizing:"border-box"}}/>
          </Card>

          {/* Designation */}
          <Card>
            <div style={{fontSize:12, fontWeight:700, color:C.mid, marginBottom:8}}>Professional Designation</div>
            <div style={{display:"flex", flexWrap:"wrap", gap:6}}>
              {DESIG.map(d => <Pill key={d} active={profile.desig===d}
                onClick={()=>setP({...profile, desig:d})}>{d}</Pill>)}
            </div>
          </Card>

          {/* City + Duration */}
          <Card>
            <div style={{fontSize:12, fontWeight:700, color:C.mid, marginBottom:8}}>City</div>
            <input type="text" value={profile.city}
              onChange={e=>setP({...profile, city:e.target.value})}
              placeholder="e.g. Silvassa, Mumbai, Delhi, London"
              style={{width:"100%", padding:"10px 12px", fontSize:14, fontFamily:C.ui,
                color:C.txt, background:"#111827",
                border:`1px solid ${profile.city?C.acc+"33":"#1e293b"}`,
                borderRadius:8, outline:"none", boxSizing:"border-box"}}/>
          </Card>

          <Card>
            <div style={{fontSize:12, fontWeight:700, color:C.mid, marginBottom:8}}>Wearable Device Usage</div>
            <div style={{display:"flex", flexWrap:"wrap", gap:6}}>
              {DURATIONS.map(d => <Pill key={d.v} active={profile.duration===d.v}
                onClick={()=>setP({...profile, duration:d.v})}>{d.l}</Pill>)}
            </div>
          </Card>

          <Btn onClick={()=>setTab(1)} disabled={!profileReady} style={{marginTop:8}}>
            {profileReady ? "Continue to Device →" : "Select gender identity and menstruation status to continue"}
          </Btn>
        </div>)}

        {/* ═══ TAB 1: DEVICE ═══ */}
        {tab===1 && (<div>
          <Label>Wearable Device & Biometrics</Label>
          <Card>
            <div style={{fontSize:12, fontWeight:700, color:C.mid, marginBottom:10}}>Device</div>
            <div style={{display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:6}}>
              {BRANDS.map(b => <Pill key={b.v} active={profile.brand===b.v}
                onClick={()=>setP({...profile, brand:b.v})}>{b.l}</Pill>)}
            </div>
          </Card>
          <Label>Biometric Data (optional)</Label>
          <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:8}}>
            {BIOFIELDS.map(f => (
              <Card key={f.k} style={{padding:12, marginBottom:0}}>
                <div style={{display:"flex", alignItems:"center", gap:6, marginBottom:6}}>
                  <span style={{fontSize:14, color:C.acc, fontFamily:C.mono}}>{f.ic}</span>
                  <span style={{fontSize:10, fontWeight:600, color:C.mid}}>{f.l}</span>
                </div>
                <div style={{display:"flex", alignItems:"center", gap:4}}>
                  <input type="number" value={wearable[f.k]}
                    onChange={e=>setW({...wearable,[f.k]:e.target.value})}
                    placeholder={f.p}
                    style={{width:"100%", padding:"8px 10px", fontSize:16, fontFamily:C.mono,
                      fontWeight:700, color:wearable[f.k]?C.txt:C.dim, background:"#0a0e17",
                      border:`1px solid ${wearable[f.k]?C.acc+"33":"#1e293b"}`,
                      borderRadius:8, outline:"none", boxSizing:"border-box"}}/>
                  <span style={{fontSize:9, color:C.dim, fontFamily:C.mono, minWidth:30}}>{f.u}</span>
                </div>
              </Card>
            ))}
          </div>
          <div style={{display:"flex", gap:8, marginTop:12}}>
            <Btn v="ghost" onClick={()=>setTab(0)} style={{flex:1}}>← Profile</Btn>
            <Btn onClick={()=>setTab(2)} style={{flex:2}}>Continue to Assessment →</Btn>
          </div>
        </div>)}

        {/* ═══ TAB 2: WA-PSS SCALE ═══ */}
        {tab===2 && (<div>
          <Label>In the last month, how often have you...</Label>
          {PSS.map((item,idx) => (
            <Card key={item.id} style={{borderColor:resp[idx]!==null?C.acc+"15":C.brd}}>
              <div style={{display:"flex", alignItems:"flex-start", gap:8, marginBottom:10}}>
                <div style={{fontSize:8, fontFamily:C.mono, color:item.r?C.acc:C.dim,
                  padding:"2px 6px", borderRadius:4, minWidth:28, textAlign:"center",
                  background:item.r?C.accD+"44":"#1e293b",
                  border:`1px solid ${item.r?C.acc+"33":"transparent"}`}}>
                  {item.id}{item.r&&<span style={{marginLeft:2,fontSize:6}}>R</span>}
                </div>
                <div style={{fontSize:12, lineHeight:1.45, color:"#cbd5e1", flex:1}}>{item.t}</div>
              </div>
              <div style={{display:"flex", gap:3}}>
                {OPT.map((o,oi) => <button key={oi}
                  onClick={()=>{const n=[...resp];n[idx]=oi;setResp(n)}}
                  style={{flex:1, padding:"7px 2px", fontSize:8, fontFamily:C.mono,
                    background:resp[idx]===oi?(item.r?C.accD:"#334155"):"#111827",
                    color:resp[idx]===oi?"#f8fafc":"#4b5563",
                    border:`1px solid ${resp[idx]===oi?(item.r?C.acc+"66":"#4b5563"):"#1e293b"}`,
                    borderRadius:6, cursor:"pointer", fontWeight:resp[idx]===oi?700:400, lineHeight:1.2}}>
                  {oi}<br/><span style={{fontSize:6, opacity:0.6}}>{o.split(" ")[0]}</span>
                </button>)}
              </div>
            </Card>
          ))}

          {/* SQ11 */}
          <Label>Additional Items</Label>
          <Card>
            <div style={{display:"flex", gap:8, marginBottom:10}}>
              <div style={{fontSize:8, fontFamily:C.mono, color:C.dim, padding:"2px 6px", borderRadius:4, background:"#1e293b"}}>SQ11</div>
              <div style={{fontSize:12, color:"#cbd5e1", lineHeight:1.45}}>I trust the health data displayed on my smartwatch.</div>
            </div>
            <div style={{display:"flex", gap:3}}>
              {OPT.map((o,oi) => <button key={oi}
                onClick={()=>{const n=[...addl];n[0]=oi;setAddl(n)}}
                style={{flex:1, padding:"7px 2px", fontSize:8, fontFamily:C.mono,
                  background:addl[0]===oi?"#334155":"#111827", color:addl[0]===oi?"#f8fafc":"#4b5563",
                  border:`1px solid ${addl[0]===oi?"#4b5563":"#1e293b"}`, borderRadius:6,
                  cursor:"pointer", fontWeight:addl[0]===oi?700:400}}>{oi}</button>)}
            </div>
          </Card>

          {/* SQ12 — ONLY IF MENSTRUATES */}
          {profile.menstruates && (
            <Card style={{borderColor:C.pink+"22"}}>
              <div style={{display:"flex", gap:8, marginBottom:10}}>
                <div style={{fontSize:8, fontFamily:C.mono, color:C.pink, padding:"2px 6px",
                  borderRadius:4, background:C.pinkD+"33"}}>SQ12</div>
                <div style={{fontSize:12, color:"#cbd5e1", lineHeight:1.45}}>I worry about my menstrual cycle data shown by my device.</div>
              </div>
              <div style={{display:"flex", gap:3}}>
                {OPT.map((o,oi) => <button key={oi}
                  onClick={()=>{const n=[...addl];n[1]=oi;setAddl(n)}}
                  style={{flex:1, padding:"7px 2px", fontSize:8, fontFamily:C.mono,
                    background:addl[1]===oi?C.pinkD:"#111827", color:addl[1]===oi?C.pink:"#4b5563",
                    border:`1px solid ${addl[1]===oi?C.pink+"55":"#1e293b"}`, borderRadius:6,
                    cursor:"pointer", fontWeight:addl[1]===oi?700:400}}>{oi}</button>)}
              </div>
            </Card>
          )}

          <div style={{display:"flex", gap:8, marginTop:8}}>
            <Btn v="ghost" onClick={()=>setTab(1)} style={{flex:1}}>← Device</Btn>
            <Btn onClick={doScore} disabled={!allDone} style={{flex:2}}>
              {allDone ? "⟨ Compute Phenotype ⟩" : `${answered}/10 completed`}
            </Btn>
          </div>
        </div>)}

        {/* ═══ TAB 3: RESULTS ═══ */}
        {tab===3 && result && (()=>{
          const m = PH[result.pheno];
          return (<div>
            <Card glow={m.bg} style={{textAlign:"center", padding:24, borderColor:m.c+"33"}}>
              <div style={{fontSize:56, fontWeight:900, fontFamily:C.mono, color:sevC[result.sev], lineHeight:1}}>{result.total}</div>
              <div style={{fontSize:9, fontFamily:C.mono, color:C.dim, letterSpacing:2, marginTop:4, textTransform:"uppercase"}}>PSS-10 Total</div>
              <div style={{display:"inline-block", marginTop:10, padding:"4px 16px",
                background:sevC[result.sev]+"15", border:`1px solid ${sevC[result.sev]}44`,
                borderRadius:20, fontSize:10, fontFamily:C.mono, fontWeight:700,
                color:sevC[result.sev], textTransform:"uppercase", letterSpacing:1.5}}>{result.sev} stress</div>
              <div style={{fontSize:10, color:C.dim, marginTop:8}}>{result.genderDisplay} · {profile.menstruates?"Menstruates":"Non-menstruating"}</div>
            </Card>

            <Card>
              <Label>Subscales</Label>
              <div style={{display:"flex", justifyContent:"space-around"}}>
                <div style={{textAlign:"center"}}><div style={{fontSize:22, fontWeight:900, fontFamily:C.mono, color:C.red}}>{result.helpless}<span style={{fontSize:11,color:C.dim}}>/24</span></div>
                  <div style={{fontSize:8, fontFamily:C.mono, color:C.dim, marginTop:2}}>HELPLESSNESS</div></div>
                <div style={{width:1, background:C.brd}}/>
                <div style={{textAlign:"center"}}><div style={{fontSize:22, fontWeight:900, fontFamily:C.mono, color:C.acc}}>{result.efficacy}<span style={{fontSize:11,color:C.dim}}>/16</span></div>
                  <div style={{fontSize:8, fontFamily:C.mono, color:C.dim, marginTop:2}}>SELF-EFFICACY</div></div>
              </div>
            </Card>

            <Card>
              <Label>EFA Factor Profile (z-scored)</Label>
              <div style={{display:"flex", gap:8}}>
                {[{l:"Emotional\nDistress",v:result.z[0],c:C.red},{l:"Self-\nEfficacy",v:result.z[1],c:C.acc},{l:"Emotional\nControl",v:result.z[2],c:C.grn}].map((f,i) =>
                  <div key={i} style={{flex:1, textAlign:"center", padding:"10px 4px", background:"#0a0e17", borderRadius:8}}>
                    <div style={{fontSize:22, fontWeight:900, fontFamily:C.mono,
                      color:Math.abs(f.v)>1.5?f.c:f.c+"bb", lineHeight:1}}>
                      {f.v>0?"+":""}{f.v.toFixed(2)}</div>
                    <div style={{fontSize:7, fontFamily:C.mono, color:C.dim, marginTop:6,
                      whiteSpace:"pre-line", lineHeight:1.3}}>{f.l}</div>
                    <div style={{marginTop:6}}><MiniBar v={Math.abs(f.v)} max={3} color={f.c}/></div>
                  </div>
                )}
              </div>
            </Card>

            <Card glow={m.bg} style={{borderColor:m.c+"44"}}>
              <Label>Digital Phenotype</Label>
              <div style={{fontSize:16, fontWeight:800, color:m.c, marginBottom:4}}>{m.l}</div>
              <div style={{fontSize:9, fontFamily:C.mono, color:C.dim, marginBottom:10}}>
                Confidence: {(result.conf*100).toFixed(1)}% · Risk: {m.r}
              </div>
              <div style={{fontSize:11, color:C.mid, lineHeight:1.6, marginBottom:12}}>{m.d}</div>
              {Object.entries(result.probs).map(([k,v]) =>
                <div key={k} style={{marginBottom:6}}>
                  <div style={{display:"flex", justifyContent:"space-between", fontSize:9, fontFamily:C.mono, color:C.dim, marginBottom:2}}>
                    <span>{PH[k].l.split(" ").slice(0,2).join(" ")}</span>
                    <span style={{color:PH[k].c}}>{(v*100).toFixed(1)}%</span>
                  </div>
                  <MiniBar v={v} max={1} color={PH[k].c}/>
                </div>
              )}
            </Card>

            <Card>
              <Label>Clinical Flags</Label>
              {[
                {f:result.tele, l:"Tele-MANAS Referral (14416)", c:C.red, ic:"⚠"},
                {f:result.ed, l:"Elevated Distress (F1 > 1.5 SD)", c:C.red, ic:"▲"},
                {f:result.le, l:"Low Self-Efficacy (F2 < -1.0 SD)", c:C.amb, ic:"▼"},
                {f:result.adapt, l:"Adaptation Phase (≤3 months)", c:C.amb, ic:"⏳"},
                {f:!!result.afabRisk, l:"AFAB + Elevated Distress", c:C.pink, ic:"⬡"},
              ].map((fl,i) =>
                <div key={i} style={{display:"flex", alignItems:"center", gap:8, padding:"8px 10px",
                  marginBottom:4, borderRadius:8, background:fl.f?fl.c+"10":"transparent",
                  border:`1px solid ${fl.f?fl.c+"33":"transparent"}`}}>
                  <span style={{fontSize:12, color:fl.f?fl.c:"#1e293b"}}>{fl.ic}</span>
                  <span style={{fontSize:11, color:fl.f?fl.c:"#334155", fontWeight:fl.f?600:400, flex:1}}>{fl.l}</span>
                  <span style={{fontSize:8, fontFamily:C.mono, color:fl.f?fl.c:"#1e293b"}}>{fl.f?"ACTIVE":"—"}</span>
                </div>
              )}
            </Card>

            <Card>
              <Label>Interventions</Label>
              {m.rx.map((r,i) =>
                <div key={i} style={{display:"flex", gap:8, padding:"8px 10px", marginBottom:4,
                  background:"#0a0e17", borderRadius:8}}>
                  <span style={{fontSize:9, fontFamily:C.mono, color:C.acc, minWidth:16}}>{i+1}.</span>
                  <span style={{fontSize:11, color:C.mid}}>{r}</span>
                </div>
              )}
            </Card>

            {result.tele && (
              <Card style={{borderColor:C.red+"44", background:"#1c0404"}}>
                <div style={{display:"flex", alignItems:"center", gap:10}}>
                  <span style={{fontSize:24}}>⚠</span>
                  <div>
                    <div style={{fontSize:13, fontWeight:800, color:C.red}}>Tele-MANAS Referral Indicated</div>
                    <div style={{fontSize:11, color:"#fca5a5", marginTop:2}}>National helpline: <strong>14416</strong></div>
                  </div>
                </div>
              </Card>
            )}

            <div style={{display:"flex", gap:8, marginTop:8}}>
              <Btn v="secondary" onClick={()=>setTab(4)} style={{flex:1}}>API Payload →</Btn>
              <Btn v="ghost" onClick={reset} style={{flex:1}}>New Assessment</Btn>
            </div>
          </div>);
        })()}

        {/* ═══ TAB 4: API ═══ */}
        {tab===4 && result && (<div>
          <Label>Production API Payload</Label>
          <Card style={{padding:12}}>
            <div style={{display:"flex", gap:8, marginBottom:6}}>
              <span style={{padding:"2px 8px", background:"#052e16", color:C.grn, borderRadius:4, fontSize:8, fontFamily:C.mono}}>OPEN</span>
              <span style={{fontSize:10, color:C.dim}}>Scale items — CC BY-NC 4.0</span>
            </div>
            <div style={{display:"flex", gap:8, marginBottom:6}}>
              <span style={{padding:"2px 8px", background:C.accD, color:"#e0f2fe", borderRadius:4, fontSize:8, fontFamily:C.mono}}>LICENSED</span>
              <span style={{fontSize:10, color:C.dim}}>Classification + flags + Temporal OS</span>
            </div>
            <div style={{display:"flex", gap:8}}>
              <span style={{padding:"2px 8px", background:"#422006", color:C.amb, borderRadius:4, fontSize:8, fontFamily:C.mono}}>TRADE SECRET</span>
              <span style={{fontSize:10, color:C.dim}}>Centroids + normalization + thresholds</span>
            </div>
          </Card>

          <Card>
            <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8}}>
              <Label>JSON Response</Label>
              <button onClick={copyJSON} style={{padding:"4px 12px", fontSize:9, fontFamily:C.mono,
                background:copied?"#052e16":C.accD, color:copied?C.grn:"#e0f2fe",
                border:`1px solid ${copied?C.grn+"44":C.acc+"44"}`, borderRadius:6, cursor:"pointer"}}>
                {copied ? "✓ Copied" : "Copy JSON"}
              </button>
            </div>
            <pre style={{fontSize:7, fontFamily:C.mono, color:C.mid, lineHeight:1.6,
              background:"#020408", padding:12, borderRadius:8, overflow:"auto",
              maxHeight:500, whiteSpace:"pre-wrap", wordBreak:"break-all",
              border:`1px solid ${C.brd}`}}>
              {JSON.stringify(result.payload, null, 2)}
            </pre>
          </Card>

          <div style={{textAlign:"center", padding:"12px 0", fontSize:8, fontFamily:C.mono, color:C.dim, lineHeight:1.8}}>
            WA-PSS © Kosambiya et al. 2026<br/>
            Scale: CC BY-NC 4.0 · Algorithm: Proprietary<br/>
            rjkosambiya@gmail.com
          </div>

          <div style={{display:"flex", gap:8, marginTop:4}}>
            <Btn v="secondary" onClick={()=>setTab(3)} style={{flex:1}}>← Results</Btn>
            <Btn v="ghost" onClick={reset} style={{flex:1}}>New Assessment</Btn>
          </div>
        </div>)}

        {(tab===3||tab===4) && !result && (
          <Card style={{textAlign:"center", padding:40}}>
            <div style={{fontSize:32, marginBottom:12}}>◈</div>
            <div style={{fontSize:14, fontWeight:700, color:C.mid, marginBottom:8}}>No Results Yet</div>
            <div style={{fontSize:11, color:C.dim, marginBottom:16}}>Complete the profile and assessment first.</div>
            <Btn onClick={()=>setTab(0)} style={{maxWidth:200, margin:"0 auto"}}>Start</Btn>
          </Card>
        )}
      </div>
    </div>
  );
}
