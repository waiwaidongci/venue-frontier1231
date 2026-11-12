import {useEffect,useState} from 'react';
import {useLocation} from '../router';
import {researchStore,loadResearch} from '../stores/research';
import {authStore,canEdit} from '../stores/auth';
import {createCase,reviseCase,approveCase,withdrawCase,exportCase,exportArchive} from '../api/cases';
import {useTask} from '../hooks/useTask';
import {number,date} from '../utils/format';
import type {Case} from '../types/domain';
import PageHeading from '../components/common/PageHeading';
import ErrorNotice from '../components/common/ErrorNotice';
import StatusBadge from '../components/common/StatusBadge';

const emptyForm={title:'',run_id:0,observation_id:0,hypothesis:'',verification:''};

export default function Cases(){
  const {query}=useLocation(),lab=researchStore.use(),{user}=authStore.use(),{busy,error,perform}=useTask();
  const [data,setData]=useState({title:'同期场馆 · 现场口径与排程复核',run_id:Number(query.get('run'))||0,observation_id:Number(query.get('observation'))||0,hypothesis:'先核对开馆时段、活动排程与能源统计边界，再讨论同伴参照对应的投入缩减空间。',verification:'安排两周现场观察并与机构联络员复核；不用于个人绩效、自动拨款或直接削减预算。'});
  const [editingId,setEditingId]=useState<number|null>(null);
  const [draft,setDraft]=useState(emptyForm);

  useEffect(()=>{perform(async()=>{
    await loadResearch();
    const run=researchStore.get().runs.find(r=>r.status==='completed'&&(!data.run_id||r.id===data.run_id));
    if(run)setData(d=>({...d,run_id:run.id,observation_id:d.observation_id||run.result.baseline?.find(r=>!r.strong_efficient)?.observation_id||run.result.baseline?.[0].observation_id||0}));
  });},[perform]);

  const run=lab.runs.find(r=>r.id===data.run_id);
  const startRevise=(c:Case)=>{setEditingId(c.id);setDraft({title:c.title,run_id:c.run_id,observation_id:c.observation_id,hypothesis:c.hypothesis,verification:c.verification});};
  const submitRevise=(c:Case)=>perform(async()=>{
    await reviseCase(c.id,{title:draft.title,hypothesis:draft.hypothesis,verification:draft.verification,expected_revision:c.revision});
    setEditingId(null);await loadResearch();
  });

  return <>
    <PageHeading index="05" title="把模型线索交给现场复核" text="现场复核可改写假设：草稿支持修订与撤回后重议，负责人按看到的版本批准；获批档案固定当时的研究指纹、机构投影与评议文字。"/>
    <ErrorNotice message={error} retry={()=>perform(loadResearch)}/>
    <div className={"cases-layout"+(canEdit(user)?"":" readonly")}>
      {canEdit(user)&&<form className="research-form" onSubmit={e=>{e.preventDefault();perform(async()=>{await createCase(data);await loadResearch();setData({...data,title:''});});}}>
        <h2>新的机构改进假设</h2>
        <label>假设标题<input value={data.title} onChange={e=>setData({...data,title:e.target.value})} minLength={2} required/></label>
        <label>依据研究<select value={data.run_id} onChange={e=>{const r=lab.runs.find(r=>r.id===Number(e.target.value));setData({...data,run_id:r?.id||0,observation_id:r?.result.baseline?.[0].observation_id||0});}}>{lab.runs.filter(r=>r.status==='completed').map(r=><option key={r.id} value={r.id}>#{r.id} {r.name}</option>)}</select></label>
        <label>目标机构<select value={data.observation_id} onChange={e=>setData({...data,observation_id:Number(e.target.value)})}>{run?.result.baseline?.map(r=><option key={r.observation_id} value={r.observation_id}>{r.venue_code} / {r.venue_name} / θ{number(r.theta,3)}</option>)}</select></label>
        <label>待验证的改进假设<textarea value={data.hypothesis} onChange={e=>setData({...data,hypothesis:e.target.value})} required minLength={10} rows={4}/></label>
        <label>现场复核计划与限制<textarea value={data.verification} onChange={e=>setData({...data,verification:e.target.value})} required minLength={10} rows={4}/></label>
        <button className="primary" disabled={busy}>保存待评议假设 →</button>
        <p className="input-note">保存后仍可在右侧反复修订；每次修订生成新版本，负责人只能按当前版本批准。</p>
      </form>}
      <section className="case-files">
        {lab.cases.map(c=>{
          const row=lab.runs.find(r=>r.id===c.run_id)?.result.baseline?.find(r=>r.observation_id===c.observation_id);
          const effective=c.archives.find(a=>a.archive_status==='effective');
          const isAdmin=user?.role==='admin';
          return <article key={c.id}>
            <div className="file-heading">
              <p className="eyebrow">INSTITUTION NOTE / {String(c.id).padStart(3,'0')} · 第 {c.revision} 版</p>
              <StatusBadge status={c.status}/>
            </div>
            <h2>{c.title}</h2>
            <div className="case-subject">
              <span>{row?.venue_name||'读取机构中'}<small>{row?.venue_code} / 依据研究#{c.run_id}</small></span>
              <b>{number(row?.theta,3)}<small>基线θ（当前研究）</small></b>
            </div>
            {editingId===c.id?<form className="revise-form" onSubmit={e=>{e.preventDefault();submitRevise(c);}}>
              <h3>修订草稿（基于第 {c.revision} 版）</h3>
              <label>假设标题<input value={draft.title} onChange={e=>setDraft({...draft,title:e.target.value})} minLength={2} required/></label>
              <label>待验证的改进假设<textarea value={draft.hypothesis} onChange={e=>setDraft({...draft,hypothesis:e.target.value})} required minLength={10} rows={3}/></label>
              <label>现场复核计划与限制<textarea value={draft.verification} onChange={e=>setDraft({...draft,verification:e.target.value})} required minLength={10} rows={3}/></label>
              <div className="revise-actions">
                <button className="primary" disabled={busy}>保存为第 {c.revision+1} 版 →</button>
                <button type="button" className="outline" disabled={busy} onClick={()=>setEditingId(null)}>放弃修订</button>
              </div>
              <p className="input-note">若他人已先一步保存修订，提交将收到版本冲突提示，需刷新后按新版本重议。</p>
            </form>:<>
              <h3>假设</h3><p>{c.hypothesis}</p>
              <h3>验证与限制</h3><p>{c.verification}</p>
            </>}
            {effective&&<div className="effective-stamp">
              <p className="eyebrow">CURRENT EFFECTIVE APPROVAL · 档案 #{effective.id} / 第 {effective.revision} 版</p>
              <p>批准人 {effective.approved_by} · {date(effective.approved_at)}</p>
              <p className="fingerprint" title="批准当时固定的研究指纹">研究指纹（固定）{effective.run_fingerprint.slice(0,24)}…</p>
            </div>}
            <footer>
              <div className="case-actions">
                {canEdit(user)&&c.status!=='approved'&&editingId!==c.id&&<button className="outline" disabled={busy} onClick={()=>startRevise(c)}>{c.status==='withdrawn'?'撤回后重议 · 修订草稿':'修订草稿 ↻'}</button>}
                {isAdmin&&c.status!=='approved'&&editingId!==c.id&&<button className="primary" disabled={busy} onClick={()=>perform(async()=>{await approveCase(c.id,c.revision);await loadResearch();})}>按第 {c.revision} 版批准 ✓</button>}
                {isAdmin&&c.status==='approved'&&<button className="outline danger" disabled={busy} onClick={()=>perform(async()=>{await withdrawCase(c.id,c.revision);await loadResearch();})}>撤回并进入重议 ↩</button>}
                {effective
                  ?<button className="text-button" disabled={busy} onClick={()=>perform(()=>exportCase(c.id))}>下载当前有效批准版 CSV ↓</button>
                  :<small className="muted">当前无有效批准版（{c.status==='withdrawn'?'旧档案已撤回':'尚待批准'}），不可下载交付</small>}
              </div>
              <small>最近更新 {date(c.updated_at)} · 历史档案 {c.archive_count} 份</small>
            </footer>
            {isAdmin&&c.archives.length>0&&<div className="archive-list">
              <h3>获批档案追溯（仅负责人可见）</h3>
              {c.archives.map(a=><div className="archive-row" key={a.id}>
                <StatusBadge status={a.archive_status}/>
                <span>档案 #{a.id} · 第 {a.revision} 版 · {a.approved_by} · {date(a.approved_at)}{a.withdrawn_at?` · 撤回于 ${date(a.withdrawn_at)}`:''}</span>
                <button className="text-button" disabled={busy} onClick={()=>perform(()=>exportArchive(c.id,a.id,a.revision))}>追溯下载 ↓</button>
              </div>)}
              <p className="input-note">档案内容不可改写：撤回后修订并重新批准只会新增档案，旧档案保留 withdrawn/superseded 状态与原始指纹、投影和评议文字。</p>
            </div>}
          </article>;
        })}
        {!lab.cases.length&&<p className="muted">完成研究后，选择一个机构，将模型线索写成可验证的现场问题。</p>}
      </section>
    </div>
  </>;
}
