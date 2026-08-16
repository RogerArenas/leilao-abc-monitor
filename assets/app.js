
// ── Dark mode ─────────────────────────────────────────────────────────────
(function(){
  var saved=localStorage.getItem('sp_theme');
  if(saved==='dark'||(!saved&&window.matchMedia('(prefers-color-scheme:dark)').matches)){
    document.documentElement.classList.add('dark');
  }
})();
function toggleDark(){
  var isDark=document.documentElement.classList.toggle('dark');
  localStorage.setItem('sp_theme',isDark?'dark':'light');
  var btn=document.getElementById('themeBtn');
  if(btn)btn.textContent=isDark?'☀️':'🌙';
}

// ── switchCalcTab com suporte a financiamento ─────────────────────────────

// Mapa de regiões → cidades (para chips de região)
var REGIOES_SP = {
  'Capital':  ['São Paulo'],
  'ABC':      ['Santo André','São Bernardo do Campo','São Caetano do Sul','Mauá','Diadema','Ribeirão Pires'],
  'GrandeSP': ['Guarulhos','Osasco','Barueri','Carapicuíba','Mogi das Cruzes','Suzano','Taboão da Serra','Cotia','Poá','Arujá','Ferraz de Vasconcelos'],
  'Litoral':  ['Santos','São Vicente','Guarujá','Praia Grande','Cubatão','Bertioga'],
  'Vale':     ['São José dos Campos','Taubaté','Jacareí','Pindamonhangaba','Guaratinguetá'],
  'Interior': ['Campinas','Sorocaba','Jundiaí','Ribeirão Preto','São José do Rio Preto','Bauru','Piracicaba','Americana','Araçatuba','Marília','São Carlos','Araraquara','Franca','Presidente Prudente','Limeira','Botucatu'],
};
var REGIAO_ATIVA = '';

function setRegiao(r, el) {
  REGIAO_ATIVA = r;
  document.querySelectorAll('.chips-bar .chip').forEach(function(c) {
    // Limpar chips de região apenas
    if (c.getAttribute('onclick') && c.getAttribute('onclick').indexOf('setRegiao') >= 0) {
      c.classList.remove('active');
    }
  });
  el.classList.add('active');
  // Limpar o select de cidade quando muda a região
  var fc = document.getElementById('fc');
  if (fc) fc.value = '';
  aplicarFiltros();
}


// ── Seleções especiais ────────────────────────────────────────────────────
var SELECAO_ATIVA='';
var CIDADES_PRAIA=['Santos','São Vicente','Guarujá','Praia Grande','Bertioga','Ubatuba','Caraguatatuba'];
var CIDADES_UNIVERSITARIO=['Campinas','São Carlos','Ribeirão Preto','Botucatu','Piracicaba','Araraquara','Franca','Bauru','Americana','São José dos Campos','Sorocaba'];
var CIDADES_TURISTICO=['São Paulo','Santos','Guarujá','Campos do Jordão','Atibaia'];
var CIDADES_AIRBNB=['Santos','Guarujá','Praia Grande','São Paulo','Campos do Jordão'];

function setSelecao(s,el){
  SELECAO_ATIVA=SELECAO_ATIVA===s?'':s;
  document.querySelectorAll('.chip-selecao').forEach(c=>c.classList.remove('active'));
  if(SELECAO_ATIVA)el.classList.add('active');
  aplicarFiltros();
}

var TODOS=[],FILT=[],FAVS={},FONTE='',LINKS=[];

/* â”€â”€ TABS â”€â”€ */
function showTab(n,el){
  document.querySelectorAll('.sec').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('.ntab').forEach(b=>b.classList.remove('active'));
  document.getElementById('tab-'+n).classList.add('active');
  el.classList.add('active');
  if(n==='caderno')renderCaderno();
  if(n==='intel')renderInteligencia();
  if(n==='alertas')carregarPerfil();
}

/* â”€â”€ SCORE â”€â”€ */
function score(im){
  var p=100;
  if(im.ocupado===true)p-=30;
  if(im.praca==='2')p-=10;
  if((im.debito_iptu||0)>0)p-=15;
  if((im.debito_cond||0)>0)p-=10;
  if(im.desagio>=35)p+=10;
  if(im.desagio<20)p-=10;
  if(!im.area)p-=3;if(!im.quartos)p-=3;
  return Math.max(0,Math.min(100,p));
}
function scoreRazoes(im){
  var r=[];
  if(im.ocupado===true)r.push('Ocupado: exige plano para posse');
  if(im.ocupado===false)r.push('Desocupado: posse tende a ser mais simples');
  if(im.praca==='2')r.push('2ª praça: confira regras do edital');
  if((im.debito_iptu||0)>0)r.push('Há IPTU informado â€” verifique valor total');
  if((im.debito_cond||0)>0)r.push('Há débito de condomínio informado');
  if(im.desagio>=35)r.push('Deságio forte frente ao avaliado');
  if(im.desagio<20)r.push('Deságio baixo para risco de leilão');
  if(!im.area)r.push('Área não informada no edital');
  if(!im.quartos)r.push('Quartos não informados no edital');
  if(!r.length)r.push('Sem alerta relevante nos dados coletados');
  return r;
}
function si(sc){
  if(sc>=70)return{lb:'Bom',cls:'good'};
  if(sc>=45)return{lb:'Médio',cls:'med'};
  return{lb:'Risco',cls:'bad'};
}

/* â”€â”€ CARREGAR â”€â”€ */
async function carregarDados(){
  mostrarSkeleton();
  try{
    var r=await fetch('dados.json?t='+Date.now());
    if(!r.ok)throw new Error('HTTP '+r.status);
    var j=await r.json();
    var imoveis=(j.imoveis||[]).filter(i=>i.lance>0);
    LINKS=j.links_consulta||[];
    if(imoveis.length===0){
      TODOS=[];
      document.getElementById('t-updated').textContent='Atualizado: '+(j.atualizado||'-')+' (sem imoveis confirmados)';
      document.getElementById('t-badge').textContent='Consulta';
      document.getElementById('t-badge').className='pill pill-info';
      document.getElementById('ist').textContent='Coleta sem imoveis confirmados. Use os links reais de consulta abaixo.';
    }else{
      TODOS=imoveis.map(im=>({...im,_sc:score(im)}));
      document.getElementById('t-updated').textContent='ðŸ“… '+(j.atualizado||'â€”');
      document.getElementById('t-badge').textContent='â— Ao vivo';
      document.getElementById('t-badge').className='pill pill-live';
      document.getElementById('ist').textContent='âœ… Dados reais â€” '+TODOS.length+' imóvel(is) · '+LINKS.length+' links';
    }
  }catch(_){
    TODOS=demo().map(im=>({...im,_sc:score(im)}));
    LINKS=[];
    document.getElementById('t-badge').textContent='âš  Demo';
    document.getElementById('t-badge').className='pill pill-demo';
    document.getElementById('t-updated').textContent='ðŸ“‹ Demonstração';
    document.getElementById('ist').textContent='âš ï¸ dados.json não encontrado â€” exibindo demonstração.';
  }
  restaurarFiltros();
  loadFavs();
  aplicarFiltros();
  var agora=new Date(),prox=new Date();prox.setHours(8,0,0,0);
  if(agora.getHours()>=8)prox.setDate(prox.getDate()+1);
  document.getElementById('iprx').textContent='⏰ Próxima atualização em ~'+Math.round((prox-agora)/3600000)+'h';
}

function setFonte(f,el){
  FONTE=f;
  document.querySelectorAll('.chip').forEach(c=>c.classList.remove('active'));
  el.classList.add('active');
  aplicarFiltros();
}

function aplicarFiltros(){
  var c=document.getElementById('fc').value;
  var mn=parseFloat(document.getElementById('fmi').value)||0;
  var mx=parseFloat(document.getElementById('fma').value)||999999;
  var q=document.getElementById('fq').value;
  var oc=document.getElementById('fo').value;
  var s=document.getElementById('fs').value;
  var textoEl=document.getElementById('ftexto');
  var txt=textoEl?(textoEl.value||'').toLowerCase().trim():'';

  FILT=TODOS.filter(im=>{
    if(!im.lance||im.lance<=0)return false;
    // Filtro por região
    if(REGIAO_ATIVA&&REGIOES_SP[REGIAO_ATIVA]&&REGIOES_SP[REGIAO_ATIVA].indexOf(im.cidade)===-1)return false;
    // Seleções especiais
    if(SELECAO_ATIVA==='airbnb'&&CIDADES_AIRBNB.indexOf(im.cidade)===-1)return false;
    if(SELECAO_ATIVA==='praia'&&CIDADES_PRAIA.indexOf(im.cidade)===-1)return false;
    if(SELECAO_ATIVA==='universitario'&&CIDADES_UNIVERSITARIO.indexOf(im.cidade)===-1)return false;
    if(SELECAO_ATIVA==='turistico'&&CIDADES_TURISTICO.indexOf(im.cidade)===-1)return false;
    if(SELECAO_ATIVA==='negativo'&&im.praca!=='2')return false;
    if(c&&im.cidade!==c)return false;
    if(FONTE&&im.fonte!==FONTE)return false;
    if(im.lance<mn||im.lance>mx)return false;
    if(q==='1'&&im.quartos!==1)return false;
    if(q==='2'&&im.quartos!==2)return false;
    if(q==='3'&&(im.quartos||0)<3)return false;
    if(oc==='livre'&&im.ocupado!==false)return false;
    if(oc==='ocp'&&im.ocupado!==true)return false;
    if(txt){
      var hay=((im.titulo||'')+' '+(im.bairro||'')+' '+(im.cidade||'')+' '+(im.matricula||'')+' '+(im.fonte||'')).toLowerCase();
      if(!hay.includes(txt))return false;
    }
    return true;
  });
  if(s==='novo')FILT.sort((a,b)=>(b.novo?1:0)-(a.novo?1:0)||b._sc-a._sc);
  if(s==='score')FILT.sort((a,b)=>b._sc-a._sc);
  if(s==='desagio')FILT.sort((a,b)=>b.desagio-a.desagio);
  if(s==='lance')FILT.sort((a,b)=>a.lance-b.lance);
  salvarFiltros();
  renderCards();stats();
}

function stats(){
  var l=FILT.length?FILT:TODOS.filter(i=>i.lance>0);
  var nb=document.getElementById('nb-busca');
  var hc=document.getElementById('h-count');
  if(!l.length){
    ['st1','st2','st3','st4','st5'].forEach(id=>document.getElementById(id).textContent='â€”');
    nb.textContent='0';nb.className='nbadge';
    hc.textContent='0 imóveis';
    return;
  }
  var lances=l.map(i=>i.lance),desagios=l.map(i=>i.desagio||0);
  var deb=l.filter(i=>(i.debito_iptu||0)>0||(i.debito_cond||0)>0).length;
  var novos=l.filter(i=>i.novo).length;
  document.getElementById('st1').textContent=l.length;
  document.getElementById('st2').textContent='R$'+Math.min(...lances).toLocaleString('pt-BR');
  document.getElementById('st3').textContent=Math.max(...desagios)+'%';
  document.getElementById('st4').textContent=novos;
  document.getElementById('st5').textContent=deb;
  nb.textContent=l.length;nb.className='nbadge on';
  hc.textContent=l.length+' imóvel(is)';
}

/* â”€â”€ CARDS â”€â”€ */
function renderCards(){
  var lista=FILT;
  document.getElementById('rcnt').textContent=lista.length+' apartamento(s)'+(FONTE?' · fonte: '+FONTE:'');
  if(!lista.length){
    var linksHtml='';
    if(LINKS.length){
      var grp={};
      LINKS.forEach(l=>{var k=l.fonte+'|'+l.cidade;if(!grp[k]){grp[k]=l;}});
      var items=Object.values(grp).slice(0,8).map(l=>
        `<a class="link-item" href="${l.url}" target="_blank" rel="noopener">
          <span><span class="li-src">${l.fonte}</span><br>${l.cidade}</span>
          <span class="link-arrow">â†—</span>
        </a>`).join('');
      linksHtml=`<div style="margin-top:1.5rem"><p style="font-size:13px;color:var(--text2);margin-bottom:.75rem;font-weight:600">Confira estes links enquanto não há preço confirmado:</p><div class="links-grid-small">${items}</div></div>`;
    }
    document.getElementById('resultado').innerHTML=`<div class="empty"><div class="empty-icon">ðŸ¢</div><div class="empty-title">Nenhum imóvel com preço confirmado nesses filtros</div><p style="font-size:13px;color:var(--text3)">Tente ampliar os critérios ou confira os links de busca manual</p>${linksHtml}</div>`;
    return;
  }
  var html='<div class="grid">';
  lista.forEach((im,idx)=>{
    var sc=im._sc,s=si(sc);
    var isD=(im.debito_iptu||0)>0||(im.debito_cond||0)>0;
    var isFav=!!FAVS[im.id||('_'+idx)];
    var ot=im.ocupado===true?'Ocupado':im.ocupado===false?'Desocupado':'Verificar';
    var otc=im.ocupado===true?'tag-occ':im.ocupado===false?'tag-free':'tag-unk';
    html+=`<div class="card" style="animation-delay:${idx*.04}s">
      <div class="card-top">
        <div class="card-header">
          <div class="card-title">${im.titulo||(im.quartos+'q · '+im.area+'m²')}</div>
          <span class="card-source">${im.fonte}</span>
        </div>
        <div class="card-location">ðŸ“ ${im.bairro?im.bairro+' · ':''}${im.cidade}</div>
        <div class="card-score">
          <div class="score-bar-wrap"><div class="score-bar ${s.cls}" style="width:${sc}%"></div></div>
          <span class="score-label ${s.cls}">Score ${sc}</span>
        </div>
        <div class="card-tags">
          ${im.novo?'<span class="tag tag-new">âœ¦ Novo</span>':'<span class="tag tag-rec">Recorrente</span>'}
          <span class="tag tag-praca">${im.praca||'?'}ª Praça</span>
          <span class="tag ${otc}">${ot}</span>
          ${im.roi_potencial?`<span class="tag tag-rec">ROI ${im.roi_potencial}%</span>`:''}
        </div>
        ${isD
          ?`<div class="debt-alert">âš  IPTU R$ ${f(im.debito_iptu)} + Cond. R$ ${f(im.debito_cond)}</div>`
          :`<div class="no-debt">âœ… Sem débitos registrados no edital</div>`
        }
        <div class="price-block">
          <div class="price-row"><span class="price-key">Avaliado</span><span class="price-old">R$ ${f(im.avaliado)}</span></div>
          <div class="price-row">
            <span class="price-key">Lance mínimo</span>
            <span class="price-main">R$ ${f(im.lance)}</span>
          </div>
          <div class="price-row"><span class="price-key">Deságio</span><span class="price-discount">-${im.desagio}%</span></div>
        </div>
        <div class="meta-grid">
          <div class="meta-item"><span class="meta-key">Área</span><span class="meta-val">${im.area?im.area+'m²':'â€”'}</span></div>
          <div class="meta-item"><span class="meta-key">Data Leilão</span><span class="meta-val" style="font-size:11px">${im.data_leilao||'â€”'}</span></div>
          <div class="meta-item"><span class="meta-key">Quartos</span><span class="meta-val">${im.quartos||'â€”'}</span></div>
          <div class="meta-item"><span class="meta-key">Matrícula</span><span class="meta-val" style="font-size:11px">${im.matricula||'â€”'}</span></div>
        </div>
        ${im.mudanca?`<div style="background:var(--green-bg);border:1px solid var(--green-border);border-radius:var(--r2);padding:.5rem .75rem;font-size:11px;color:var(--green);font-family:'JetBrains Mono',monospace">â†• ${im.mudanca}</div>`:''}
      </div>
      <div class="card-actions">
        <button class="btn-fav ${isFav?'active':''}" onclick="toggleFav('${im.id||('_'+idx)}',${idx},this)" title="Favoritar">⭐</button>
        <button class="btn-cmp" onclick="toggleCompare('${im.id||('_'+idx)}',${idx},this)" title="Comparar âš–ï¸">âš–ï¸</button>
        <a href="${im.url}" target="_blank" rel="noopener" class="btn-edital" onclick="event.stopPropagation()">Ver Edital â†—</a>
        <button class="btn-detail" onclick="abrirModal(${idx})">Analisar â†’</button>
      </div>
    </div>`;
  });
  html+='</div>';
  document.getElementById('resultado').innerHTML=html;
}

/* â”€â”€ INTELIGÊNCIA â”€â”€ */
function renderInteligencia(){
  var lista=TODOS.filter(i=>i.lance>0).sort((a,b)=>(b.roi_potencial||0)-(a.roi_potencial||0)||b._sc-a._sc);
  var el=document.getElementById('intel-lista');
  document.getElementById('ir1').textContent=lista.length;
  document.getElementById('ir4').textContent=lista.filter(i=>i.novo).length;
  if(!lista.length){
    document.getElementById('ir2').textContent='â€”';document.getElementById('ir3').textContent='â€”';
    var linksH='';
    if(LINKS.length){
      var grp2={};LINKS.forEach(l=>{var k=l.fonte+'|'+l.cidade;if(!grp2[k]){grp2[k]=l;}});
      linksH=`<div class="links-grid-small" style="margin-top:1rem">${Object.values(grp2).slice(0,8).map(l=>`<a class="link-item" href="${l.url}" target="_blank" rel="noopener"><span><span class="li-src">${l.fonte}</span><br>${l.cidade}</span><span class="link-arrow">â†—</span></a>`).join('')}</div>`;
    }
    el.innerHTML=`<div class="empty"><div class="empty-icon">ðŸ“Š</div><div class="empty-title">Sem imóveis confirmados</div><p style="font-size:13px;color:var(--text3)">Use os links de conferência manual para alimentar a próxima coleta.</p>${linksH}</div>`;
    return;
  }
  var roiMed=Math.round(lista.reduce((s,i)=>s+(i.roi_potencial||0),0)/lista.length);
  document.getElementById('ir2').textContent=roiMed+'%';
  document.getElementById('ir3').textContent=Math.max(...lista.map(i=>i._sc))+'/100';
  var html='<div class="mode-grid">';
  lista.forEach(im=>{
    var cls=(im.roi_potencial||0)>=15?'good':(im.roi_potencial||0)>=5?'warn':'risk';
    html+=`<div class="mode-card ${cls}">
      <div class="mode-name">${im.novo?'âœ¦ Novo · ':''}${im.titulo}</div>
      <div class="mode-desc">${im.cidade} · ${im.fonte}<br>Estratégia: ${im.estrategia_sugerida||'Analisar edital e mercado'}</div>
      <div class="price-block" style="margin-bottom:0">
        <div class="price-row"><span class="price-key">Investimento total</span><span style="font-size:13px;font-weight:700;color:var(--primary)">R$ ${f(im.custo_total)}</span></div>
        <div class="price-row"><span class="price-key">Valor mercado est.</span><span style="font-size:13px;font-weight:600">R$ ${f(im.valor_mercado_estimado||im.avaliado)}</span></div>
        <div class="price-row"><span class="price-key">ROI potencial</span><span style="font-size:13px;font-weight:700;color:${(im.roi_potencial||0)>=0?'var(--green)':'var(--red)'}">${im.roi_potencial||0}%</span></div>
      </div>
      <div class="mode-tags" style="margin-top:.75rem">
        <span class="mode-tag">Score ${im._sc}</span>
        <span class="mode-tag">Localiz. ${im.qualidade_localizacao||'â€”'}/100</span>
        <span class="mode-tag">${im.ocupado===true?'Ocupado':im.ocupado===false?'Desocupado':'Ocp. a confirmar'}</span>
      </div>
    </div>`;
  });
  html+='</div>';el.innerHTML=html;
}

/* â”€â”€ MODAL â”€â”€ */


// ── Calculadora de Financiamento (SAC/Price) ─────────────────────────────
function calcFinanciamento(){
  var lance=parseFloat(document.getElementById('clf-lance').value)||0;
  var entrada=parseFloat(document.getElementById('clf-entrada').value)||20;
  var taxa=parseFloat(document.getElementById('clf-taxa').value)||10;
  var meses=parseInt(document.getElementById('clf-meses').value)||120;
  var sist=document.getElementById('clf-sist').value||'price';
  var venda=parseFloat(document.getElementById('clf-venda').value)||0;
  var fAluguel=parseFloat(document.getElementById('clf-aluguel').value)||0;

  var financed=lance*(1-entrada/100);
  var taxaMes=taxa/12/100;
  var parcela=0, totalPago=0;

  if(sist==='price'){
    parcela=financed*(taxaMes*Math.pow(1+taxaMes,meses))/(Math.pow(1+taxaMes,meses)-1);
    totalPago=parcela*meses+(lance*entrada/100);
  } else { // SAC
    var amort=financed/meses;
    var firstP=amort+financed*taxaMes;
    var lastP=amort+amort*taxaMes;
    totalPago=(firstP+lastP)/2*meses+(lance*entrada/100);
    parcela=firstP;
  }

  var com=Math.round(lance*.05),itbi=Math.round(lance*.03),cart=3500,ref=15000;
  var custoTotal=totalPago+com+itbi+cart+ref;
  var roi=venda>0?Math.round(((venda-custoTotal)/custoTotal)*100):0;
  var aluguelAnual=fAluguel*12;
  var yieldAluguel=aluguelAnual>0?((aluguelAnual/custoTotal)*100).toFixed(1):0;

  document.getElementById('clf-result').innerHTML=`
    <div class="calc-result-grid">
      <div class="calc-res-item"><span class="calc-res-label">1ª Parcela (${sist.toUpperCase()})</span><span class="calc-res-val">R$ ${f(Math.round(parcela))}</span></div>
      <div class="calc-res-item"><span class="calc-res-label">Total financiado</span><span class="calc-res-val">R$ ${f(Math.round(financed))}</span></div>
      <div class="calc-res-item"><span class="calc-res-label">Total pago (financ.)</span><span class="calc-res-val">R$ ${f(Math.round(totalPago))}</span></div>
      <div class="calc-res-item"><span class="calc-res-label">Custo total real</span><span class="calc-res-val warn">R$ ${f(Math.round(custoTotal))}</span></div>
      ${venda>0?`<div class="calc-res-item"><span class="calc-res-label">Lucro na revenda</span><span class="calc-res-val ${roi>=0?'green':'red'}">R$ ${f(Math.round(venda-custoTotal))} (${roi}%)</span></div>`:''}
      ${yieldAluguel>0?`<div class="calc-res-item"><span class="calc-res-label">Yield locação anual</span><span class="calc-res-val green">${yieldAluguel}% a.a.</span></div>`:''}
    </div>`;
}

// ── Exportar PDF do modal ─────────────────────────────────────────────────
function exportarPDF_old(){
  window.print();
}
function exportarPDF(){
  var m=document.getElementById('mbody');
  if(!m)return;
  var clone=m.cloneNode(true);
  var w=window.open('','_blank');
  w.document.write('<html><head><title>SP Leilões — Análise</title><style>body{font-family:system-ui;padding:20px;max-width:700px;margin:auto;color:#1e293b}.ipl-seg,.ql-wrap,.chk-legal{margin-bottom:16px;padding:12px;border:1px solid #e2e8f0;border-radius:8px}.modal-section{margin-bottom:16px}.modal-section-title{font-weight:700;margin-bottom:8px;color:#f97316}.modal-row{display:flex;justify-content:space-between;border-bottom:1px solid #f1f5f9;padding:4px 0}.cost-row{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #f1f5f9}.ipl-seg-bar{height:10px;background:#22c55e;border-radius:4px;display:inline-block}.ql-bar-bg{width:120px;height:6px;background:#e2e8f0;border-radius:3px;display:inline-block}.ql-bar-fill{height:100%;background:#3b82f6;border-radius:3px}.chk-row{padding:4px 0;display:flex;gap:8px}.green{color:#16a34a}.red{color:#dc2626}.warn{color:#d97706}</style></head><body>');
  w.document.write('<h2 style="color:#1a2744">SP Leilões — Análise do Imóvel</h2>');
  w.document.write('<p style="font-size:11px;color:#64748b">Gerado em '+new Date().toLocaleString('pt-BR')+'</p>');
  w.document.write(clone.innerHTML);
  w.document.write('</body></html>');
  w.document.close();
  setTimeout(()=>w.print(),400);
}

// ── IPL Segmentado (Ninja-style) ──────────────────────────────────────────
function iplSegmentado(im){
  var sc=im._sc||0;
  // Decompor: Margem 60%, Risco 30%, Oportunidade 10%
  var desagio=im.desagio||0;
  var margemScore=Math.min(60,Math.round(desagio*1.5));   // máx 60
  var riscoPts=0;
  if(im.ocupado===false)riscoPts+=15;
  if((im.debito_iptu||0)===0)riscoPts+=8;
  if((im.debito_cond||0)===0)riscoPts+=7;
  var riscoScore=Math.min(30,riscoPts);
  var opPts=0;
  if(im.praca==='1')opPts+=5;
  if(im.novo)opPts+=3;
  if((im.area||0)>=50)opPts+=2;
  var opScore=Math.min(10,opPts);
  var total=margemScore+riscoScore+opScore;
  var cls=total>=70?'ipl-good':total>=45?'ipl-med':'ipl-bad';
  return `<div class="ipl-seg">
    <div class="ipl-seg-hd">
      <span class="ipl-seg-label">IPL <span class="ipl-seg-num ${cls}">${total}/100</span></span>
      <span class="ipl-seg-hint">Margem · Risco · Oportunidade</span>
    </div>
    <div class="ipl-bar-wrap">
      <div class="ipl-seg-bar" style="width:${margemScore}%" title="Margem: ${margemScore}/60"></div>
      <div class="ipl-seg-bar ipl-orange" style="width:${riscoScore/30*margemScore}%;margin-left:2px" title="Risco: ${riscoScore}/30"></div>
      <div class="ipl-seg-bar ipl-blue" style="width:${opScore/10*margemScore*0.3}%;margin-left:2px" title="Oportunidade: ${opScore}/10"></div>
    </div>
    <div class="ipl-seg-detail">
      <span title="Margem de lucro potencial (60% do score)">📈 Margem <b>${margemScore}</b><small>/60</small></span>
      <span title="Risco jurídico e débitos (30% do score)">⚖️ Risco <b>${riscoScore}</b><small>/30</small></span>
      <span title="Oportunidade de momento (10% do score)">⚡ Opor. <b>${opScore}</b><small>/10</small></span>
    </div>
  </div>`;
}


// ── Checklist legal visual (Ninja-style) ─────────────────────────────────
function checklistLegal(im){
  var items=[
    {label:'Ocupação',   ok:im.ocupado===false, warn:im.ocupado===true,   icon:'🏠', detalhe:im.ocupado===false?'Desocupado':im.ocupado===true?'Ocupado — risco':'Verificar edital'},
    {label:'Praça',      ok:im.praca==='1',     warn:im.praca==='2',      icon:'⚖️', detalhe:im.praca==='1'?'1ª Praça — preço inicial':im.praca==='2'?'2ª Praça — já sem lance antes, maior desconto':'Verificar'},
    {label:'IPTU',       ok:!im.debito_iptu,    warn:(im.debito_iptu||0)>0,icon:'🏛️',detalhe:(im.debito_iptu||0)>0?'R$ '+f(im.debito_iptu)+' pendente':'Sem débito registrado'},
    {label:'Condomínio', ok:!im.debito_cond,    warn:(im.debito_cond||0)>0,icon:'🏢',detalhe:(im.debito_cond||0)>0?'R$ '+f(im.debito_cond)+' pendente':'Sem débito registrado'},
    {label:'Matrícula',  ok:!!im.matricula,     warn:false,               icon:'📄', detalhe:im.matricula?'Nº '+im.matricula:'Não informada — buscar no cartório'},
  ];
  var rows=items.map(it=>{
    var st=it.warn?'chk-red':it.ok?'chk-green':'chk-gray';
    var ic=it.warn?'❌':it.ok?'✅':'❓';
    return `<div class="chk-row ${st}"><span class="chk-ico">${ic}</span><span class="chk-nm">${it.icon} ${it.label}</span><span class="chk-dt">${it.detalhe}</span></div>`;
  }).join('');
  // Badge 2ª praça especial
  var praca2=im.praca==='2'?'<div class="praca2-badge">🔁 2ª Praça — preço geralmente 40–60% abaixo do valor de mercado. Lance pode ser menor que na 1ª praça.</div>':'';
  return `<div class="chk-legal">${rows}</div>${praca2}`;
}

// ── Qualidade de localização visual ──────────────────────────────────────
function qualidadeLocalizacao(im){
  var base_ql={
    'São Caetano do Sul':{seg:90,trp:80,srv:85,laz:78},
    'São Paulo':{seg:68,trp:90,srv:92,laz:85},
    'Santo André':{seg:72,trp:78,srv:80,laz:72},
    'São Bernardo do Campo':{seg:70,trp:75,srv:78,laz:70},
    'Mauá':{seg:62,trp:65,srv:65,laz:58},
    'Guarulhos':{seg:65,trp:72,srv:75,laz:65},
    'Campinas':{seg:68,trp:78,srv:82,laz:75},
    'Santos':{seg:72,trp:75,srv:80,laz:82},
    'São José dos Campos':{seg:74,trp:72,srv:78,laz:72},
    'Sorocaba':{seg:70,trp:68,srv:72,laz:68},
    'Ribeirão Preto':{seg:70,trp:70,srv:78,laz:72},
    'Jundiaí':{seg:74,trp:72,srv:75,laz:70},
  };
  var ql=base_ql[im.cidade]||{seg:62,trp:60,srv:62,laz:58};
  var total=Math.round((ql.seg+ql.trp+ql.srv+ql.laz)/4);
  var cls=total>=75?'ipl-good':total>=60?'ipl-med':'ipl-bad';
  function bar(v,label,icon){
    return `<div class="ql-row"><span class="ql-label">${icon} ${label}</span><div class="ql-bar-bg"><div class="ql-bar-fill" style="width:${v}%"></div></div><span class="ql-val">${v}</span></div>`;
  }
  return `<div class="ql-wrap">
    <div class="ql-score-hd">Qualidade da Localização <span class="ipl-seg-num ${cls}">${total}/100</span></div>
    ${bar(ql.seg,'Segurança','🛡️')}
    ${bar(ql.trp,'Transporte','🚌')}
    ${bar(ql.srv,'Serviços','🏪')}
    ${bar(ql.laz,'Lazer','🌳')}
  </div>`;
}


// ── Sparkline histórico de lances ────────────────────────────────────────
function sparklineHistorico(im){
  if(!im.historico_lances||im.historico_lances.length<2) return '';
  var vals=im.historico_lances.map(h=>h.lance||h);
  var mn=Math.min(...vals),mx=Math.max(...vals);
  var w=220,h=50,pad=4;
  var pts=vals.map((v,i)=>{
    var x=pad+i*(w-pad*2)/(vals.length-1);
    var y=pad+(1-(v-mn)/(mx-mn||1))*(h-pad*2);
    return x+','+y;
  }).join(' ');
  var last=vals[vals.length-1],first=vals[0];
  var dir=last>first?'↑ subiu':'↓ caiu';
  var clr=last<=first?'#22c55e':'#ef4444';
  return `<div class="spark-wrap">
    <div class="spark-hd">Histórico de lances <span style="color:${clr};font-size:11px">${dir} ${Math.round(Math.abs((last-first)/first*100))}%</span></div>
    <svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" class="sparkline">
      <polyline points="${pts}" fill="none" stroke="${clr}" stroke-width="1.5"/>
      <circle cx="${pts.split(' ').at(-1).split(',')[0]}" cy="${pts.split(' ').at(-1).split(',')[1]}" r="3" fill="${clr}"/>
    </svg>
    <div class="spark-range">R$ ${f(mn)} — R$ ${f(mx)}</div>
  </div>`;
}

function abrirModal(idx){
  var im=FILT[idx];if(!im)return;
  var sc=im._sc,s=si(sc);
  var razoes=scoreRazoes(im).map(x=>`<li style="margin-bottom:.25rem">${x}</li>`).join('');
  var com=Math.round(im.lance*.05),itbi=Math.round(im.lance*.03),cart=3500;
  var ref=im.area?Math.round(im.area*400):15000;
  var deb=(im.debito_iptu||0)+(im.debito_cond||0);
  var total=im.lance+com+itbi+cart+ref+deb;
  document.getElementById('mtit').textContent=im.titulo||(im.quartos+'q · '+im.area+'m² â€” '+im.cidade);
  document.getElementById('msub').textContent='ðŸ“ '+(im.bairro?im.bairro+' â€” ':'')+im.cidade+'  |  '+im.fonte+(im.data_leilao?'  |  ðŸ“… '+im.data_leilao:'');
  var favId=im.id||('_'+idx);
  var mapsUrl=im.lat&&im.lng?'https://www.google.com/maps?q='+im.lat+','+im.lng:'https://www.google.com/maps/search/?api=1&query='+encodeURIComponent((im.bairro||im.titulo)+', '+im.cidade+' SP');
  document.getElementById('mbody').innerHTML=
    renderValorMercado(im)+iplSegmentado(im)+checklistLegal(im)+qualidadeLocalizacao(im)+renderLocaisProximos(im)+sparklineHistorico(im)+`
    <div class="modal-section">
      <div class="modal-section-title">ðŸ“Š Dados do Imóvel</div>
      ${im.quartos?`<div class="modal-row"><span class="modal-row-key">Quartos</span><span class="modal-row-val">${im.quartos}</span></div>`:''}
      ${im.area?`<div class="modal-row"><span class="modal-row-key">Área</span><span class="modal-row-val">${im.area} m²</span></div>`:''}
      <div class="modal-row"><span class="modal-row-key">Cidade</span><span class="modal-row-val">${im.cidade}${im.bairro?' â€” '+im.bairro:''}</span></div>
      ${im.matricula?`<div class="modal-row"><span class="modal-row-key">Matrícula</span><span class="modal-row-val">${im.matricula}</span></div>`:''}
      <div class="modal-row"><span class="modal-row-key">Praça</span><span class="modal-row-val">${im.praca}ª Praça</span></div>
      <div class="modal-row"><span class="modal-row-key">Histórico</span><span class="modal-row-val ${im.novo?'green':''}">${im.novo?'âœ¦ Novo desde a última coleta':'Já visto antes'}</span></div>
      <div class="modal-row"><span class="modal-row-key">Score</span><span class="modal-row-val"><span class="score-label ${s.cls}">${s.lb} (${sc}/100)</span></span></div>
      <div class="modal-row"><span class="modal-row-key">Estratégia sugerida</span><span class="modal-row-val">${im.estrategia_sugerida||'Analisar edital'}</span></div>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">ðŸ’° Valores</div>
      <div class="modal-row"><span class="modal-row-key">Avaliado</span><span class="modal-row-val">R$ ${f(im.avaliado)}</span></div>
      <div class="modal-row"><span class="modal-row-key">Lance mínimo</span><span class="modal-row-val green">R$ ${f(im.lance)}</span></div>
      <div class="modal-row"><span class="modal-row-key">Deságio</span><span class="modal-row-val green">-${im.desagio}%</span></div>
      <div class="modal-row"><span class="modal-row-key">ROI potencial</span><span class="modal-row-val ${(im.roi_potencial||0)>=0?'green':'red'}">${im.roi_potencial||0}%</span></div>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">âš ï¸ Situação e Débitos</div>
      <div class="modal-row"><span class="modal-row-key">Ocupação</span><span class="modal-row-val ${im.ocupado?'red':'green'}">${im.ocupado===true?'ðŸš¨ Ocupado':im.ocupado===false?'âœ… Desocupado':'â“ Verificar'}</span></div>
      <div class="modal-row"><span class="modal-row-key">Débito IPTU</span><span class="modal-row-val ${(im.debito_iptu||0)>0?'red':'green'}">R$ ${f(im.debito_iptu||0)}</span></div>
      <div class="modal-row"><span class="modal-row-key">Débito Condomínio</span><span class="modal-row-val ${(im.debito_cond||0)>0?'red':'green'}">R$ ${f(im.debito_cond||0)}</span></div>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">ðŸ§­ Leitura do Score</div>
      <ul style="margin:0 0 0 18px;color:var(--text2);font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.9">${razoes}</ul>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">ðŸ§® Custo Real Total</div>
      <div class="cost-table">
        <div class="cost-row"><span class="ck">Lance mínimo</span><span class="cv">R$ ${f(im.lance)}</span></div>
        <div class="cost-row"><span class="ck">Comissão leiloeiro (5%)</span><span class="cv">R$ ${f(com)}</span></div>
        <div class="cost-row"><span class="ck">ITBI â€” Imp. transferência (3%)</span><span class="cv">R$ ${f(itbi)}</span></div>
        <div class="cost-row"><span class="ck">Escritura / Cartório</span><span class="cv">R$ ${f(cart)}</span></div>
        <div class="cost-row"><span class="ck">Reforma estimada (R$400/m²)</span><span class="cv">R$ ${f(ref)}</span></div>
        ${deb>0?`<div class="cost-row"><span class="ck">Débitos assumidos</span><span class="cv" style="color:#dc2626">R$ ${f(deb)}</span></div>`:''}
        <div class="cost-row"><span class="ck">ðŸ’° TOTAL QUE VOCÊ VAI PAGAR</span><span class="cv">R$ ${f(total)}</span></div>
      </div>
    </div>
    <div class="checklist-box">
      <strong>ðŸ“‹ Antes do lance â€” verifique:</strong><br>
      â‘  Leia o edital completo no site do leiloeiro<br>
      â‘¡ Consulte IPTU na Prefeitura de ${im.cidade}<br>
      â‘¢ Ligue para síndico â€” débito de condomínio<br>
      â‘£ Verifique matrícula no Cartório de Registro<br>
      â‘¤ Confirme situação de ocupação e prazo<br>
      â‘¥ Defina seu lance máximo e não passe
    </div>
    <div class="modal-actions">
      <a href="${im.url}" target="_blank" rel="noopener" class="modal-btn modal-btn-primary">Ver Edital Oficial â†—</a>
      <a href="${mapsUrl}" target="_blank" rel="noopener" class="modal-btn modal-btn-secondary">🗺️ Mapa</a>
      <button class="modal-btn modal-btn-secondary" onclick="favModal('${favId}',${idx})">⭐ Caderno</button>
      <button class="modal-btn modal-btn-secondary" onclick="exportarPDF()" title="Gerar PDF">📄 PDF</button>
    </div>`;
  document.getElementById('modal').classList.add('open');
}
function fecharModal(){document.getElementById('modal').classList.remove('open');}
function favModal(fid,idx){toggleFav(fid,idx,null);fecharModal();alert('âœ… Salvo no caderno! Acesse a aba ⭐ Caderno.');}

/* â”€â”€ FAVS â”€â”€ */
function loadFavs(){try{FAVS=JSON.parse(localStorage.getItem('leilao_favs_v2')||'{}')}catch(_){FAVS={}}updFavBadge();}
function saveFavs(){localStorage.setItem('leilao_favs_v2',JSON.stringify(FAVS));updFavBadge();}
function updFavBadge(){var n=Object.keys(FAVS).length,el=document.getElementById('nb-fav');el.textContent=n;el.className='nbadge'+(n>0?' on':'');}
function toggleFav(fid,idx,btn){
  var im=FILT[idx];if(!im)return;
  var k=fid||im.id||('_'+idx);
  if(FAVS[k]){delete FAVS[k];if(btn)btn.classList.remove('active');}
  else{
    FAVS[k]={id:k,titulo:im.titulo||(im.quartos+'q · '+im.area+'m²'),cidade:im.cidade,bairro:im.bairro||'',lance:im.lance,desagio:im.desagio,fonte:im.fonte,url:im.url,sc:im._sc,saved:new Date().toLocaleDateString('pt-BR'),nota:'',checks:{iptu:false,cond:false,mat:false,ocup:false,edital:false,lmax:false}};
    if(btn)btn.classList.add('active');
  }
  saveFavs();
}
function renderCaderno(){
  var ks=Object.keys(FAVS),el=document.getElementById('caderno');
  if(!ks.length){el.innerHTML='<div class="caderno-empty"><div class="ei">ðŸ“’</div><p>Caderno vazio</p><small>Clique em ⭐ em qualquer imóvel para salvar aqui</small></div>';return;}
  var cls={iptu:'â‘  Consultei IPTU na Prefeitura',cond:'â‘¡ Liguei para síndico (condomínio)',mat:'â‘¢ Verifiquei matrícula no Cartório',ocup:'â‘£ Confirmei situação de ocupação',edital:'â‘¤ Li o edital completo',lmax:'â‘¥ Defini meu lance máximo'};
  var html='<div class="fav-grid">';
  ks.forEach(k=>{
    var fv=FAVS[k],s=si(fv.sc);
    var checks=fv.checks||{};
    var totalChk=Object.keys(cls).length;
    var doneChk=Object.values(checks).filter(Boolean).length;
    var pctChk=Math.round((doneChk/totalChk)*100);
    var ch=Object.keys(cls).map(c=>`<div class="fav-ci ${checks[c]?'done':''}" onclick="togCheck('${k}','${c}',this)"><input type="checkbox" ${checks[c]?'checked':''} onclick="event.stopPropagation()"> ${cls[c]}</div>`).join('');
    html+=`<div class="fav-card">
      <div class="fav-head"><div><div class="fav-title">${fv.titulo}</div><span class="score-label ${s.cls}" style="margin-top:5px;display:inline-block">${s.lb}</span></div><button class="fav-del" onclick="remFav('${k}')">âœ•</button></div>
      <div class="fav-meta">ðŸ“ ${fv.bairro?fv.bairro+' · ':''}${fv.cidade} · ${fv.fonte}<br>ðŸ’° R$ ${f(fv.lance)} · -${fv.desagio}% · Salvo ${fv.saved}</div>
      <div class="chk-progress">
        <div class="chk-progress-hd"><span>Due diligence</span><span id="prg-lbl-${k}">${doneChk}/${totalChk}</span></div>
        <div class="chk-progress-bar"><div class="chk-progress-fill" id="prg-${k}" style="width:${pctChk}%"></div></div>
      </div>
      <div class="fav-nota"><textarea placeholder="Suas anotações sobre este imóvel..." onchange="savNota('${k}',this.value)">${fv.nota||''}</textarea></div>
      <div class="fav-check">${ch}</div>
      <div style="display:flex;gap:7px;margin-top:.875rem">
        <a href="${fv.url}" target="_blank" rel="noopener" class="fav-link" style="flex:1">Ver Edital â†—</a>
        ${PERFIL&&PERFIL.escola?`<a href="https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent((fv.bairro||fv.titulo)+', '+fv.cidade+', SP')}&waypoints=${encodeURIComponent(PERFIL.escola)}" target="_blank" rel="noopener" class="fav-link" style="flex:1;color:var(--green);border-color:var(--green-border);background:var(--green-bg)">ðŸ—ºï¸ Rota escola</a>`:``}
      </div>
    </div>`;
  });
  html+='</div>';el.innerHTML=html;
}
function togCheck(k,c,el){
  if(!FAVS[k])return;
  FAVS[k].checks[c]=!FAVS[k].checks[c];
  saveFavs();
  var r=el.closest('.fav-ci');
  r.classList.toggle('done',FAVS[k].checks[c]);
  r.querySelector('input').checked=FAVS[k].checks[c];
  var total=6,done=Object.values(FAVS[k].checks).filter(Boolean).length,pct=Math.round((done/total)*100);
  var bar=document.getElementById('prg-'+k);if(bar)bar.style.width=pct+'%';
  var lbl=document.getElementById('prg-lbl-'+k);if(lbl)lbl.textContent=done+'/'+total;
}
function savNota(k,v){if(FAVS[k]){FAVS[k].nota=v;saveFavs();}}
function remFav(k){delete FAVS[k];saveFavs();renderCaderno();}
function limparFavs(){if(confirm('Apagar todos os favoritos?')){FAVS={};saveFavs();renderCaderno();}}

/* â”€â”€ CALCULADORAS â”€â”€ */
function calcC(){
  var l=parseFloat(document.getElementById('cl').value)||0;
  var a=parseFloat(document.getElementById('ca').value)||0;
  var d=parseFloat(document.getElementById('cd').value)||0;
  if(!l){document.getElementById('ctb').style.display='none';return;}
  var com=Math.round(l*.05),itbi=Math.round(l*.03),cart=3500,ref=a?Math.round(a*400):15000;
  var tot=l+com+itbi+cart+ref+d;
  document.getElementById('r1').textContent='R$ '+f(l);
  document.getElementById('r2').textContent='R$ '+f(com);
  document.getElementById('r3').textContent='R$ '+f(itbi);
  document.getElementById('r4').textContent='R$ '+f(cart);
  document.getElementById('r5').textContent='R$ '+f(ref);
  document.getElementById('r6').textContent='R$ '+f(d);
  document.getElementById('ctv').textContent='R$ '+f(tot);
  document.getElementById('cts').textContent=a?'Custo por m²: R$ '+f(tot/a)+'/m²':'';
  document.getElementById('ctb').style.display='block';
}
function calcR(){
  var o=parseFloat(document.getElementById('ro').value)||0;
  var a=parseFloat(document.getElementById('ra').value)||0;
  var d=parseFloat(document.getElementById('rd').value)||0;
  var ref=parseFloat(document.getElementById('rr').value)||(a?a*400:15000);
  if(!o){document.getElementById('rb').style.display='none';return;}
  var fixos=3500+ref+d;
  var lmax=Math.floor((o-fixos)/1.08);
  if(lmax<0)lmax=0;
  var tax=Math.round(lmax*.08);
  document.getElementById('rr1').textContent='R$ '+f(o);
  document.getElementById('rr2').textContent='R$ '+f(tax);
  document.getElementById('rr3').textContent='R$ '+f(ref);
  document.getElementById('rr4').textContent='R$ '+f(d);
  document.getElementById('rv').textContent='R$ '+f(lmax);
  document.getElementById('rb').style.display='block';
}

/* â”€â”€ DEMO â”€â”€ */
function demo(){
  var cs=['São Paulo','Santo André','São Bernardo do Campo','Mauá','São Caetano do Sul',
          'Guarulhos','Campinas','Santos','São José dos Campos','Sorocaba','Ribeirão Preto','Osasco'];
  var bs={
    'São Paulo':['Tatuapé','Santana','Ipiranga','Vila Prudente','Penha'],
    'Santo André':['Paraíso','Vila Bastos','Cidade São Jorge'],
    'São Bernardo do Campo':['Baeta Neves','Paulista','Ferrazópolis'],
    'Mauá':['Centro','Vila Bocaina','Apura'],
    'São Caetano do Sul':['Boa Vista','Santo Antônio','Cerâmica'],
    'Guarulhos':['Centro','Macedo','Jardim Angélica'],
    'Campinas':['Cambuí','Taquaral','Jardim Aurélia'],
    'Santos':['Boqueirão','José Menino','Embaré'],
    'São José dos Campos':['Centro','Jardim Aquarius','Vila Adyana'],
    'Sorocaba':['Centro','Além Ponte','Jardim Wanel Ville'],
    'Ribeirão Preto':['Centro','Jardim Irajá','Higienópolis'],
    'Osasco':['Centro','Presidente Altino','Jardim Veloso'],
  };
  var fs=['Caixa','Sold','Zuk','Superbid','Banco do Brasil'];
  var us={'Caixa':'https://venda.caixa.gov.br/imoveis?estado=SP','Sold':'https://www.sold.com.br','Zuk':'https://www.portalzuk.com.br','Superbid':'https://www.superbid.net','Banco do Brasil':'https://leiloes.bb.com.br'};
  return Array.from({length:16},(_,i)=>{
    var c=cs[i%cs.length],l=72000+Math.floor(Math.random()*88000),av=l+Math.floor(Math.random()*60000);
    var fn=fs[i%fs.length],q=1+Math.floor(Math.random()*3),a=48+Math.floor(Math.random()*72);
    var td=Math.random()>.55,dt=new Date();dt.setDate(dt.getDate()+5+Math.floor(Math.random()*40));
    var id='demo_'+i+'_'+l;
    return{id,titulo:q+'q · '+a+'m²',cidade:c,bairro:bs[c][Math.floor(Math.random()*bs[c].length)],lance:l,avaliado:av,desagio:Math.round(((av-l)/av)*100),fonte:fn,url:us[fn],praca:Math.random()>.35?'1':'2',ocupado:Math.random()>.5,debito_iptu:td?Math.round(Math.random()*12000):0,debito_cond:td?Math.round(Math.random()*7000):0,area:a,quartos:q,matricula:'R.'+(10000+Math.floor(Math.random()*90000)),data_leilao:dt.toLocaleDateString('pt-BR'),roi_potencial:Math.round(Math.random()*25-5),estrategia_sugerida:'Analisar edital e mercado',qualidade_localizacao:65+Math.floor(Math.random()*25)};
  });
}

function f(n){return Math.round(n||0).toLocaleString('pt-BR');}

// â”€â”€ LOGOUT â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function fazerLogout(){
  if(!confirm('Deseja sair do monitor?'))return;
  sessionStorage.removeItem('abc_leilao_auth');
  localStorage.removeItem('abc_leilao_auth');
  window.location.replace('login.html');
}

document.addEventListener('keydown',e=>{if(e.key==='Escape'){fecharModal();if(typeof fecharModalCmp!=='undefined')fecharModalCmp();}});

/* â”€â”€ FILTROS PERSISTENTES â”€â”€ */
function salvarFiltros(){
  try{localStorage.setItem('leilao_filtros_v2',JSON.stringify({
    regiao:REGIAO_ATIVA,
    c:document.getElementById('fc').value,
    mn:document.getElementById('fmi').value,
    mx:document.getElementById('fma').value,
    q:document.getElementById('fq').value,
    oc:document.getElementById('fo').value,
    s:document.getElementById('fs').value,
    txt:(document.getElementById('ftexto')||{}).value||'',
    fonte:FONTE,
  }));}catch(_){}
}
function restaurarFiltros(){
  try{
    var fil=JSON.parse(localStorage.getItem('leilao_filtros_v2')||'{}');
    if(fil.c)document.getElementById('fc').value=fil.c;
    if(fil.regiao!==undefined){REGIAO_ATIVA=fil.regiao;document.querySelectorAll('[onclick*="setRegiao"]').forEach(function(el){if(el.getAttribute('onclick').includes("'"+fil.regiao+"'")||(!fil.regiao&&el.getAttribute('onclick').includes("''"))){el.classList.add('active');}else{el.classList.remove('active');}});}
    if(fil.mn)document.getElementById('fmi').value=fil.mn;
    if(fil.mx)document.getElementById('fma').value=fil.mx;
    if(fil.q)document.getElementById('fq').value=fil.q;
    if(fil.oc)document.getElementById('fo').value=fil.oc;
    if(fil.s)document.getElementById('fs').value=fil.s;
    var fte=document.getElementById('ftexto');if(fte&&fil.txt)fte.value=fil.txt;
    if(fil.fonte){
      FONTE=fil.fonte;
      document.querySelectorAll('.chip').forEach(c=>c.classList.remove('active'));
      if(!FONTE)document.querySelector('.chip').classList.add('active');
    }
  }catch(_){}
}
function limparFiltros(){
  ['fc','fq','fo'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('fmi').value='70000';
  document.getElementById('fma').value='500000';
  var fte=document.getElementById('ftexto');if(fte)fte.value='';
  document.getElementById('fs').value='novo';
  FONTE='';
  document.querySelectorAll('.chip').forEach(c=>c.classList.remove('active'));
  document.querySelector('.chip').classList.add('active');
  localStorage.removeItem('leilao_filtros_v2');
  aplicarFiltros();
}

/* â”€â”€ DEBOUNCE â”€â”€ */
var _debTimer=null;
function filtroDebounce(){clearTimeout(_debTimer);_debTimer=setTimeout(aplicarFiltros,350);}

/* â”€â”€ SKELETON â”€â”€ */
function mostrarSkeleton(){
  document.getElementById('resultado').innerHTML='<div class="grid">'+
    Array.from({length:6},()=>`<div class="skel-card"><div class="skeleton skel-line skel-med"></div><div class="skeleton skel-line skel-short"></div><div class="skeleton skel-tall" style="margin-top:1rem"></div><div class="skeleton skel-line skel-med" style="margin-top:1rem"></div><div class="skeleton skel-line skel-short"></div></div>`).join('')+
  '</div>';
}

/* â”€â”€ COMPARADOR â”€â”€ */
var COMPARE=[];
function toggleCompare(id,idx,btn){
  var im=FILT[idx];if(!im)return;
  var pos=COMPARE.findIndex(x=>x.id===id);
  if(pos>=0){COMPARE.splice(pos,1);btn.classList.remove('active');}
  else{
    if(COMPARE.length>=3){alert('Máximo 3 imóveis para comparar.');return;}
    COMPARE.push(im);btn.classList.add('active');
  }
  atualizarCompareBar();
}
function atualizarCompareBar(){
  var bar=document.getElementById('cbar');
  if(!COMPARE.length){bar.classList.remove('show');return;}
  bar.classList.add('show');
  document.getElementById('citems').innerHTML=COMPARE.map((im,i)=>
    `<div class="compare-item-pill">${im.titulo.substring(0,28)}<button onclick="removerCompare(${i})">×</button></div>`
  ).join('');
}
function removerCompare(i){COMPARE.splice(i,1);atualizarCompareBar();}
function limparCompare(){COMPARE=[];atualizarCompareBar();}
function abrirComparador(){
  if(COMPARE.length<2){alert('Selecione pelo menos 2 imóveis para comparar.');return;}
  var campos=[
    ['Cidade','cidade',v=>v],
    ['Lance','lance',v=>'R$ '+f(v)],
    ['Avaliado','avaliado',v=>'R$ '+f(v)],
    ['Deságio','desagio',v=>v+'%'],
    ['Área','area',v=>v?v+'m²':'â€”'],
    ['Quartos','quartos',v=>v||'â€”'],
    ['Ocupação','ocupado',v=>v===true?'Ocupado':v===false?'Desocupado':'?'],
    ['Score','_sc',v=>v+'/100'],
    ['Praça','praca',v=>(v||'?')+'ª'],
    ['Custo Total','custo_total',v=>v?'R$ '+f(v):'â€”'],
    ['ROI','roi_potencial',v=>v+'%'],
    ['Data','data_leilao',v=>v||'â€”'],
  ];
  var best={
    lance:Math.min(...COMPARE.map(i=>i.lance)),
    desagio:Math.max(...COMPARE.map(i=>i.desagio||0)),
    _sc:Math.max(...COMPARE.map(i=>i._sc||0)),
    roi_potencial:Math.max(...COMPARE.map(i=>i.roi_potencial||0)),
  };
  var worst={lance:Math.max(...COMPARE.map(i=>i.lance))};
  var header='<tr><th>Campo</th>'+COMPARE.map(im=>`<th>${im.titulo.substring(0,22)}<br><span class="score-label ${si(im._sc).cls}" style="font-size:9px">${si(im._sc).lb}</span></th>`).join('')+'</tr>';
  var rows=campos.map(([lbl,key,fmt])=>{
    var cells=COMPARE.map(im=>{
      var v=im[key];
      var cls='';
      if(key in best&&v===best[key])cls='best';
      if(key==='lance'&&v===worst.lance&&COMPARE.length>1)cls='worst';
      return`<td class="${cls}">${fmt(v)}</td>`;
    }).join('');
    return`<tr><td class="rl">${lbl}</td>${cells}</tr>`;
  }).join('');
  document.getElementById('cmp-body').innerHTML=
    `<div style="overflow-x:auto"><table class="cmp-table"><thead>${header}</thead><tbody>${rows}</tbody></table></div>`+
    `<p style="font-size:11px;color:var(--text3);font-family:'JetBrains Mono',monospace;margin-top:1rem">ðŸŸ¢ Verde = melhor · ðŸ”´ Vermelho = pior</p>`;
  document.getElementById('modal-cmp').classList.add('open');
}
function fecharModalCmp(){document.getElementById('modal-cmp').classList.remove('open');}

/* â”€â”€ CALC TABS â”€â”€ */
function showCalcTab(i,el){
  document.querySelectorAll('.calc-tab').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.cp').forEach(p=>p.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('cp'+i).classList.add('active');
}

/* â”€â”€ CALC FINANCIAMENTO â”€â”€ */
function calcF(){
  var pv=parseFloat(document.getElementById('fv').value)||0;
  var i=parseFloat(document.getElementById('fi').value)/100||0;
  var n=parseFloat(document.getElementById('fn').value)||0;
  var rb=document.getElementById('frb');
  if(!pv||!i||!n){rb.style.display='none';return;}
  var pmt=pv*i/(1-Math.pow(1+i,-n));
  var total=pmt*n,juros=total-pv;
  document.getElementById('fv1').textContent='R$ '+f(pv);
  document.getElementById('fv2').textContent=(i*100).toFixed(2)+'% a.m.';
  document.getElementById('fv3').textContent=n+' meses ('+(n/12).toFixed(1)+' anos)';
  document.getElementById('fv4').textContent='R$ '+f(total);
  document.getElementById('fv5').textContent='R$ '+f(juros)+' ('+Math.round((juros/pv)*100)+'% do principal)';
  document.getElementById('frv').textContent='R$ '+f(pmt);
  document.getElementById('frs').textContent='Total de juros: R$ '+f(juros);
  rb.style.display='block';
}

/* â”€â”€ CALC VALOR/m² â”€â”€ */
function calcM(){
  var v=parseFloat(document.getElementById('mv').value)||0;
  var a=parseFloat(document.getElementById('ma').value)||0;
  var mercado=parseFloat(document.getElementById('mc').value)||3800;
  var rb=document.getElementById('mrb');
  if(!v||!a){rb.style.display='none';['mv1','mv2','mv3','ms1','ms2'].forEach(id=>document.getElementById(id).textContent='â€”');return;}
  var meu=Math.round(v/a),dif=mercado-meu,pct=Math.round((dif/mercado)*100);
  document.getElementById('mv1').textContent='R$ '+f(meu)+'/m²';
  document.getElementById('mv2').textContent='R$ '+f(mercado)+'/m²';
  document.getElementById('mv3').textContent=(dif>=0?'R$ '+f(dif)+' mais barato':'R$ '+f(Math.abs(dif))+' mais caro')+' que o mercado';
  var ms1=document.getElementById('ms1');ms1.textContent='R$ '+f(meu);
  ms1.className='m2-ref-val '+(meu<=mercado*.8?'ok':meu<=mercado?'med':'high');
  document.getElementById('ms2').textContent='R$ '+f(mercado);
  document.getElementById('mrv').textContent=(pct>=0?'-'+pct+'%':'+'+Math.abs(pct)+'%')+' vs mercado';
  document.getElementById('mrs').textContent=pct>=0?'Economia de R$ '+f(dif*a)+' vs compra no mercado':'Acima do mercado â€” reavalie';
  rb.style.display='block';
}

/* â”€â”€ PERFIL â”€â”€ */
var PERFIL={};
function initPerfil(){try{PERFIL=JSON.parse(localStorage.getItem('leilao_perfil')||'{}');}catch(_){PERFIL={};}}
function salvarPerfil(){
  PERFIL={
    min:(document.getElementById('pl-min')||{}).value||'',
    max:(document.getElementById('pl-max')||{}).value||'',
    q:(document.getElementById('pl-q')||{}).value||'',
    escola:((document.getElementById('pl-escola')||{}).value||'').trim(),
  };
  localStorage.setItem('leilao_perfil',JSON.stringify(PERFIL));
  var s=document.getElementById('pf-saved');if(s){s.style.display='block';setTimeout(()=>s.style.display='none',2500);}
  if(PERFIL.min&&document.getElementById('fmi'))document.getElementById('fmi').value=PERFIL.min;
  if(PERFIL.max&&document.getElementById('fma'))document.getElementById('fma').value=PERFIL.max;
  if(PERFIL.q&&document.getElementById('fq'))document.getElementById('fq').value=PERFIL.q;
  aplicarFiltros();
}
function carregarPerfil(){
  try{
    PERFIL=JSON.parse(localStorage.getItem('leilao_perfil')||'{}');
    if(PERFIL.min&&document.getElementById('pl-min'))document.getElementById('pl-min').value=PERFIL.min;
    if(PERFIL.max&&document.getElementById('pl-max'))document.getElementById('pl-max').value=PERFIL.max;
    if(PERFIL.q&&document.getElementById('pl-q'))document.getElementById('pl-q').value=PERFIL.q;
    if(PERFIL.escola&&document.getElementById('pl-escola'))document.getElementById('pl-escola').value=PERFIL.escola;
  }catch(_){}
}

/* â”€â”€ PDF / EXPORT â”€â”€ */
function switchCalcTab(id,el){
  ['basica','reversa','financiamento','m2'].forEach(function(t){
    var p=document.getElementById('tc-'+t);
    if(p)p.style.display=(t===id)?'block':'none';
  });
  document.querySelectorAll('.calc-tabs .tab').forEach(function(t){t.classList.remove('active')});
  if(el)el.classList.add('active');
}// Mapa de regiões → cidades (para chips de região)
var REGIOES_SP = {
  'Capital':  ['São Paulo'],
  'ABC':      ['Santo André','São Bernardo do Campo','São Caetano do Sul','Mauá','Diadema','Ribeirão Pires'],
  'GrandeSP': ['Guarulhos','Osasco','Barueri','Carapicuíba','Mogi das Cruzes','Suzano','Taboão da Serra','Cotia','Poá','Arujá','Ferraz de Vasconcelos'],
  'Litoral':  ['Santos','São Vicente','Guarujá','Praia Grande','Cubatão','Bertioga'],
  'Vale':     ['São José dos Campos','Taubaté','Jacareí','Pindamonhangaba','Guaratinguetá'],
  'Interior': ['Campinas','Sorocaba','Jundiaí','Ribeirão Preto','São José do Rio Preto','Bauru','Piracicaba','Americana','Araçatuba','Marília','São Carlos','Araraquara','Franca','Presidente Prudente','Limeira','Botucatu'],
};
var REGIAO_ATIVA = '';


// ── MAPA LEAFLET ──────────────────────────────────────────────────────────
var _mapaInit = false;
var _mapaObj  = null;
var _mapaMarkers = [];

function renderMapa(){
  if(!window.L){ setTimeout(renderMapa, 300); return; }
  var container = document.getElementById('mapa-leaflet');
  if(!container) return;

  if(!_mapaInit){
    _mapaObj = L.map('mapa-leaflet').setView([-23.55, -46.63], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
      attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom:19
    }).addTo(_mapaObj);
    _mapaInit = true;
  }

  // Limpar marcadores anteriores
  _mapaMarkers.forEach(m=>m.remove());
  _mapaMarkers = [];

  var imoveis = FILT.filter(im=>im.lat && im.lng && im.lance > 0);
  if(!imoveis.length){
    document.getElementById('mapa-leaflet').insertAdjacentHTML('beforeend',
      '<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;padding:1rem 1.5rem;border-radius:.75rem;box-shadow:0 4px 20px rgba(0,0,0,.15);z-index:1000;font-size:.85rem;text-align:center">'+
      '📍 Nenhum imóvel com coordenadas.<br><small>Execute o coletor para geocodificar.</small></div>'
    );
    return;
  }

  var bounds = [];
  imoveis.forEach(function(im,idx){
    var sc   = im._sc || 0;
    var cor  = sc >= 7 ? '#16a34a' : sc >= 4 ? '#d97706' : '#dc2626';
    var icon = L.divIcon({
      className:'',
      html:'<div style="width:32px;height:32px;border-radius:50%;background:'+cor+';border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.3);display:flex;align-items:center;justify-content:center;color:#fff;font-size:11px;font-weight:700">'+sc+'</div>',
      iconSize:[32,32], iconAnchor:[16,16], popupAnchor:[0,-16]
    });
    var popup = '<div style="min-width:180px;font-size:.78rem">' +
      '<strong style="display:block;margin-bottom:.3rem;font-size:.82rem">'+(im.titulo||im.cidade)+'</strong>'+
      '<div style="color:#64748b;margin-bottom:.4rem">📍 '+(im.bairro||im.cidade)+'</div>'+
      '<div style="font-size:1rem;font-weight:700;color:#1a2744">'+fr(im.lance)+'</div>'+
      '<div style="font-size:.7rem;color:#64748b">Deságio: '+(im.desagio||0)+'%  |  IPL: '+(im._sc||'?')+'/10</div>'+
      '<button onclick="abrirModal('+idx+')" style="margin-top:.5rem;width:100%;background:#1a2744;color:#fff;border:none;padding:.35rem;border-radius:.375rem;cursor:pointer;font-size:.75rem">Analisar →</button>'+
      '</div>';
    var marker = L.marker([im.lat, im.lng], {icon:icon}).addTo(_mapaObj).bindPopup(popup);
    _mapaMarkers.push(marker);
    bounds.push([im.lat, im.lng]);
  });

  if(bounds.length) _mapaObj.fitBounds(bounds, {padding:[30,30]});
  setTimeout(()=>_mapaObj.invalidateSize(), 200);
}


  var el = document.getElementById('modal-content') || document.getElementById('mbody');
  if(!el){ window.print(); return; }

  if(window.html2pdf){
    var titulo = (document.getElementById('mtit')||{}).textContent || 'imovel';
    var nome   = 'SP-Leiloes-'+titulo.replace(/[^a-zA-Z0-9]/g,'-').slice(0,40)+'.pdf';
    html2pdf().set({
      margin:10, filename:nome, pagebreak:{mode:['avoid-all']},
      image:{type:'jpeg',quality:.95},
      html2canvas:{scale:2},
      jsPDF:{unit:'mm',format:'a4',orientation:'portrait'}
    }).from(el).save();
  } else {
    window.print();
  }
}

// ── VALOR DE MERCADO (exibição no modal) ────────────────────────────────────
function renderValorMercado(im){
  var vm = im.valor_mercado;
  if(!vm || !vm.estimado) return '';
  var lance = im.lance || 0;
  var pct   = vm.estimado > 0 ? Math.max(0, Math.min(100, (lance/vm.estimado)*100)) : 0;
  var desagio = vm.estimado > 0 ? ((vm.estimado - lance)/vm.estimado*100).toFixed(1) : 0;
  var cls = desagio >= 20 ? 'bom' : desagio >= 0 ? '' : 'ruim';
  return '<div class="vm-wrap">'+
    '<div class="vm-title">💹 Valor de Mercado Estimado</div>'+
    '<div class="vm-range">'+
      '<span class="vm-val">'+fr(vm.min)+'</span>'+
      '<div class="vm-bar-bg">'+
        '<div class="vm-bar-fill" style="left:0;width:'+pct+'%"></div>'+
        '<div class="vm-lance" style="left:'+pct+'%"></div>'+
      '</div>'+
      '<span class="vm-val">'+fr(vm.max)+'</span>'+
    '</div>'+
    '<span class="vm-desagio '+cls+'">'+
      (desagio >= 0 ? '🟢' : '🔴')+' '+desagio+'% abaixo do mercado'+
      (vm.amostras ? ' ('+vm.amostras+' anúncios)' : '')+
    '</span>'+
    '<div class="vm-fonte">Fonte: '+(vm.fonte==='serper_olx_zap'?'OLX · ZAP · VivaReal':'estimativa local')+'</div>'+
  '</div>';
}

// ── LOCAIS PRÓXIMOS (exibição no modal) ─────────────────────────────────────
function renderLocaisProximos(im){
  var lp = im.locais_proximos;
  if(!lp || !Object.keys(lp).length) return '';
  var rows = Object.values(lp).map(function(l){
    var d = l.dist_m || 0;
    var cls = d < 500 ? 'perto' : d < 1500 ? '' : 'longe';
    var txt = d < 1000 ? d+'m' : (d/1000).toFixed(1)+'km';
    return '<div class="lp-row">'+
      '<span class="lp-icon">'+l.label.split(' ')[0]+'</span>'+
      '<span class="lp-label">'+l.nome+'</span>'+
      '<span class="lp-dist '+cls+'">'+txt+'</span>'+
    '</div>';
  }).join('');
  return '<div class="lp-wrap">'+
    '<div class="lp-title">📍 Locais Próximos</div>'+rows+'</div>';
}
