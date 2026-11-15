(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const money = value => `₹${Number(value || 0).toLocaleString('en-IN')}`;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const state = { students: [], items: [], pool: null, request: null, activeLoan: null, scanner: null, countdown: null, selectedPurchase: null };
  const api = async (path, options = {}) => {
    const response = await fetch(path, { ...options, headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers } });
    let data = {}; try { data = await response.json(); } catch {}
    if (!response.ok) throw new Error(data.detail || data.message || `Request failed (${response.status})`);
    return data;
  };
  const set = (selector, value) => { const node = $(selector); if (node) node.textContent = value ?? ''; };
  const message = (selector, value, error = false) => { const node = $(selector); if (node) { node.textContent = value || ''; node.classList.toggle('error', error); } };
  function notify(text, error = false) { const toast = $('#toast'); if (!toast) return; toast.textContent = text; toast.classList.toggle('error', error); toast.hidden = false; clearTimeout(state.toastTimer); state.toastTimer = setTimeout(() => { toast.hidden = true; }, 4500); }
  async function checkHealth() {
    const dot = $('#health-dot'), label = $('#health-label'); if (!dot || !label) return;
    try { await api('/health'); dot.className = 'dot online'; label.textContent = 'API connected'; }
    catch { dot.className = 'dot offline'; label.textContent = 'API offline'; }
  }
  function updateBandwidth() {
    const resources = performance.getEntriesByType('resource').filter(resource => /cdnjs\.cloudflare|unpkg\.com\/lenis/i.test(resource.name));
    const bytes = resources.reduce((total, resource) => total + (resource.transferSize || resource.encodedBodySize || 0), 0);
    set('#bandwidth-note', `Observed optional motion CDN transfer this page load: about ${Math.ceil(bytes / 1024)} KiB. Lite mode pauses motion; already-downloaded CDN bytes are not saved.`);
  }
  function setupPreferences() {
    const lite = $('#lite-toggle'), contrast = $('#contrast-toggle');
    const liteOn = localStorage.getItem('campusloop-lite') === 'true';
    document.body.classList.toggle('lite', liteOn);
    if (lite) {
      lite.setAttribute('aria-pressed', String(liteOn));
      lite.addEventListener('click', () => {
        const on = document.body.classList.toggle('lite');
        localStorage.setItem('campusloop-lite', String(on));
        lite.setAttribute('aria-pressed', String(on));
        if (on && window.gsap) window.gsap.globalTimeline.pause();
        else if (window.gsap && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) window.gsap.globalTimeline.resume();
        if (on && state.lenis) state.lenis.stop();
        else if (state.lenis && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) state.lenis.start();
        updateBandwidth();
      });
    }
    const contrastOn = localStorage.getItem('campusloop-contrast') === 'true';
    document.body.classList.toggle('contrast', contrastOn);
    if (contrast) {
      contrast.setAttribute('aria-pressed', String(contrastOn));
      contrast.addEventListener('click', () => {
        const on = document.body.classList.toggle('contrast');
        localStorage.setItem('campusloop-contrast', String(on));
        contrast.setAttribute('aria-pressed', String(on));
      });
    }
    updateBandwidth();
    window.addEventListener('load', updateBandwidth, { once: true });
  }
  function normalizeList(data, key) { if (Array.isArray(data)) return data; return data?.[key] || data?.results || []; }
  async function loadStudents() {
    const data = await api('/api/students');
    state.students = normalizeList(data, 'students');
    const storageKeys = {
      '#current-student': 'campusloop-student',
      '#buyer-select': 'campusloop-buyer',
      '#item-owner': 'campusloop-owner',
      '#borrower-id': 'campusloop-borrower',
      '#loan-student': 'campusloop-loan-student'
    };
    for (const selector of Object.keys(storageKeys)) {
      const select = $(selector);
      if (!select) continue;
      const prior = localStorage.getItem(storageKeys[selector]) || select.value;
      select.innerHTML = (selector === '#buyer-select' || selector === '#loan-student' ? '<option value="">Choose demo student</option>' : '') + state.students.map(student => `<option value="${esc(student.id)}">${esc(student.name || student.student_name || student.id)} · Block ${esc(student.hostel_block || student.block || '—')}</option>`).join('');
      if (prior && state.students.some(student => String(student.id) === prior)) select.value = prior;
      select.addEventListener('change', () => localStorage.setItem(storageKeys[selector], select.value));
    }
    const selected = $('#current-student');
    if (selected && !selected.value && state.students[0]) selected.value = state.students[0].id;
  }
  const nameFor = id => state.students.find(student => String(student.id) === String(id))?.name || state.students.find(student => String(student.id) === String(id))?.student_name || id || 'Unknown';
  async function loadAllItems() { const data = await api('/api/items'); state.items = normalizeList(data, 'items'); return state.items; }
  async function initHome() {
    const story = $('.section[aria-labelledby="story-title"]');
    const cards = story ? $$('.card', story) : [];
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const lite = document.body.classList.contains('lite');
    if (window.gsap && window.ScrollTrigger && cards.length && !reduced && !lite && innerWidth > 760) {
      window.gsap.registerPlugin(window.ScrollTrigger);
      const timeline = window.gsap.timeline({ scrollTrigger: { trigger: story, start: 'top top', end: '+=3200', pin: true, scrub: 1, invalidateOnRefresh: true } });
      cards.forEach((card, index) => timeline.fromTo(card, { opacity: .25, y: 24 }, { opacity: 1, y: 0, duration: 1 }, index));
      state.homeTimeline = timeline;
    }
    if (!reduced && !lite && innerWidth > 760) {
      const smoothScroll = document.createElement('script');
      smoothScroll.src = 'https://unpkg.com/lenis@1.1.20/dist/lenis.min.js';
      smoothScroll.onload = () => { if (window.Lenis && !document.body.classList.contains('lite') && !window.matchMedia('(prefers-reduced-motion: reduce)').matches && innerWidth > 760) state.lenis = new window.Lenis({ autoRaf: true }); updateBandwidth(); };
      document.head.append(smoothScroll);
    }
  }
  let valuationTimer;
  async function updateValuation() {
    const form = $('#valuation-form'); if (!form) return;
    const values = ['original-price','months-used','days-used','on-time-returns','late-returns'];
    for (const [input, output] of [['original-price','price-value'],['months-used','months-value'],['days-used','days-value'],['on-time-returns','on-time-value'],['late-returns','late-value']]) set(`#${output}`, $(`#${input}`).value);
    const params = new URLSearchParams({ category: $('#category').value, condition: $('#condition').value, original_price: $('#original-price').value, months_used: $('#months-used').value, days_used: $('#days-used').value, on_time_returns: $('#on-time-returns').value, late_returns: $('#late-returns').value, items_lent: $('#items-lent')?.value || '0' });
    message('#valuation-error', 'Calculating with the CampusLoop API…');
    try {
      const result = await api(`/api/valuate?${params}`);
      for (const [key, id] of [['senior_resale_price','#senior-price'],['day_transfer_price','#day-price'],['dealer_pool_estimate','#pool-estimate'],['individual_scrap_estimate','#scrap-estimate']]) { const node = $(id); if (!node) continue; const value = money(result[key]); if (window.gsap && !document.body.classList.contains('lite') && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) { const prior = Number(node.dataset.value || 0); const target = Number(result[key] || 0); const counter = { value: prior }; window.gsap.to(counter, { value: target, duration: .4, onUpdate: () => { node.textContent = money(Math.round(counter.value)); } }); node.dataset.value = String(target); } else node.textContent = value; }
      const eligible = Boolean(result.trustlend_eligible), threshold = Number(result.trustlend_threshold || ($('#category').value === 'Academic Book' ? 50 : 65));
      const score = Math.min(100, Math.max(0, Number(result.trust_score) || 0)), ring = $('#trust-ring'), scoreNode = $('#trust-score');
      if (scoreNode && window.gsap && !document.body.classList.contains('lite') && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        const counter = { value: Number(scoreNode.dataset.value || 0) };
        window.gsap.to(counter, { value: score, duration: .45, onUpdate: () => { scoreNode.textContent = String(Math.round(counter.value)); } });
        scoreNode.dataset.value = String(score);
      } else set('#trust-score', score);
      if (ring) {
        const dash = 282.7 * (1 - score / 100);
        ring.style.stroke = eligible ? 'var(--teal)' : 'var(--coral)';
        if (window.gsap && !document.body.classList.contains('lite') && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) window.gsap.to(ring, { strokeDashoffset: dash, duration: .45 });
        else ring.style.strokeDashoffset = String(dash);
      }
      set('#threshold-text', `Category threshold: ${threshold} trust points.`);
      const box = $('#eligible-box');
      if (box) { box.textContent = eligible ? `TrustLend eligible · required threshold ${threshold}. No deposit required.` : `Not yet eligible · reach ${threshold} trust points for this category.`; box.classList.toggle('yes', eligible); box.classList.toggle('no', !eligible); }
      message('#valuation-error', 'Estimate updated from the API.');
    } catch (error) { message('#valuation-error', `Valuation unavailable: ${error.message}. Check the API connection.`, true); }
  }
  function initValuation() {
    $('#valuation-form')?.addEventListener('input', () => { clearTimeout(valuationTimer); valuationTimer = setTimeout(updateValuation, 180); });
    $('#isbn-lookup')?.addEventListener('click', async () => { const isbn = $('#isbn').value.trim().replace(/[\s-]/g, ''); if (!isbn) { message('#isbn-feedback', 'Enter an ISBN to look it up.', true); return; } message('#isbn-feedback', 'Looking up ISBN…'); try { const result = await api(`/api/isbn/${encodeURIComponent(isbn)}`); $('#category').value = result.category; $('#original-price').value = result.original_price; message('#isbn-feedback', `Found ${result.title}; category and price filled in.`); updateValuation(); } catch (error) { message('#isbn-feedback', `ISBN lookup unavailable: ${error.message}. Enter item details manually.`, true); } }); updateValuation();
  }
  function listingCard(item) {
    const price = item.mode === '₹0 TrustLend' ? '₹0 · borrow' : money(item.mode === 'Day Transfer' ? item.day_transfer_price : item.senior_resale_price);
    return `<article class="card item-card"><span class="tag">${esc(item.category)}</span><h3>${esc(item.title || item.name || 'Campus item')}</h3><div class="item-meta"><span>Block ${esc(item.hostel_block || item.block || '—')}</span><span>${esc(item.condition || 'Good')}</span><span>${esc(item.mode)}</span></div><div class="item-price">${price}</div><p class="muted">Owner: ${esc(item.owner_name || nameFor(item.owner_id))} (${esc(item.owner_id)})</p><div class="item-actions"><span class="badge">${item.available === false ? 'Unavailable' : 'Available'}</span>${item.available !== false && item.mode !== '₹0 TrustLend' ? `<button class="btn primary buy-item" data-id="${esc(item.id)}" type="button">Buy</button>` : ''}</div></article>`;
  }
  async function ensureGsap() {
    if (window.gsap) return true;
    return new Promise(resolve => {
      const script = document.createElement('script');
      script.src = 'https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js';
      script.onload = () => resolve(Boolean(window.gsap));
      script.onerror = () => resolve(false);
      document.head.append(script);
    });
  }
  async function loadMarketplace() {
    const params = new URLSearchParams(); for (const [select,key] of [['#filter-category','category'],['#filter-mode','mode'],['#filter-block','hostel_block']]) if ($(select)?.value) params.set(key,$(select).value);
    set('#market-status','Loading listings…');
    try {
      const grid = $('#items-grid');
      if (window.Flip && !window.gsap) await ensureGsap();
      if (window.Flip && window.gsap) window.gsap.registerPlugin(window.Flip);
      const prior = window.Flip && window.gsap && grid && !document.body.classList.contains('lite') && !window.matchMedia('(prefers-reduced-motion: reduce)').matches ? window.Flip.getState('.item-card') : null;
      const data = await api(`/api/items${params.size ? `?${params}` : ''}`); const items = normalizeList(data,'items'); state.items = items;
      grid.innerHTML = items.length ? items.map(listingCard).join('') : '<div class="empty">No available listings match these filters.</div>';
      if (prior && grid.querySelector('.item-card')) window.Flip.from(prior,{duration:.35,absolute:true,stagger:.025,ease:'power1.inOut'});
      set('#market-status',`${items.length} listing${items.length === 1 ? '' : 's'} loaded.`);
    } catch(error) {
      console.error(error);
      set('#market-status',`Marketplace offline: ${error.message}. Retry by changing a filter.`);
      $('#items-grid').innerHTML = '<div class="empty">Listings are unavailable while the API is offline.</div>';
    }
  }
  async function history() { const studentId = $('#buyer-select')?.value || $('#current-student')?.value; if (!studentId) { set('#purchase-history','Choose a demo student to see history.'); return; } set('#purchase-history','Loading purchase history…'); try { const data = await api(`/api/purchases?student_id=${encodeURIComponent(studentId)}`); const rows = normalizeList(data,'purchases'); $('#purchase-history').innerHTML = rows.length ? rows.map(order => `<div class="history-row"><strong>${esc(order.item_title || order.title || `Order ${order.order_id || order.id}`)}</strong><div>${esc(order.buyer_name || nameFor(order.buyer_id))} bought from ${esc(order.seller_name || nameFor(order.seller_id))} · ${money(order.amount)} · payment status: ${esc(order.payment_status || 'simulated')}</div></div>`).join('') : '<p class="muted">No buyer or seller orders recorded for this student.</p>'; } catch(error) { set('#purchase-history',`Purchase history unavailable: ${error.message}`); } }
  function initMarketplace() {
    for (const selector of ['#filter-category','#filter-mode','#filter-block']) $(selector)?.addEventListener('change',loadMarketplace);
    $('#items-grid')?.addEventListener('click', event => { const button = event.target.closest('.buy-item'); if (!button) return; const item = state.items.find(entry => String(entry.id) === button.dataset.id); state.selectedPurchase = item; if (!item) { loadMarketplace(); return; } const buyer = $('#buyer-select')?.value || $('#current-student')?.value; if (!buyer) { notify('Choose a demo buyer identity first.',true); return; } $('#purchase-confirmation').textContent = `${nameFor(buyer)} will purchase ${item.title || item.name} from ${item.owner_name || nameFor(item.owner_id)} for ${money(item.mode === 'Day Transfer' ? item.day_transfer_price : item.senior_resale_price)}. Payment status will be simulated only.`; $('#purchase-modal').showModal(); });
    $('#buyer-select')?.addEventListener('change', history); $('#refresh-history')?.addEventListener('click',history);
    $('#create-form')?.addEventListener('submit', async event => { event.preventDefault(); const form=event.currentTarget; const data=Object.fromEntries(new FormData(form).entries()); data.original_price=Number(data.original_price); data.months_used=Number(data.months_used||0); data.days_used=Number(data.days_used||0); const target=$('#create-error'); target.textContent='Submitting listing…'; try { await api('/api/items',{method:'POST',body:JSON.stringify(data)}); form.reset(); $('#create-modal').close(); notify('Listing created.'); loadMarketplace(); } catch(error) { target.textContent=`Could not create listing: ${error.message}`; } });
    $('#open-create')?.addEventListener('click',() => { const select=$('#item-owner'), current=$('#current-student')?.value; if (current) select.value=current; $('#create-modal').showModal(); }); $('#close-create')?.addEventListener('click',()=>$('#create-modal').close());
    $('#purchase-form')?.addEventListener('submit',async event=>{event.preventDefault(); const item=state.selectedPurchase, buyer=$('#buyer-select')?.value || $('#current-student')?.value; if(!item||!buyer)return; $('#purchase-error').textContent='Recording simulated purchase…'; try { const result=await api('/api/purchases',{method:'POST',body:JSON.stringify({item_id:item.id,buyer_id:buyer})}); $('#purchase-modal').close(); notify(`Purchase recorded · simulated payment status: ${result.payment_status || 'simulated'}.`); await Promise.all([loadMarketplace(),history()]); } catch(error) { $('#purchase-error').textContent=`Purchase was not recorded: ${error.message}`; } });
    $('#close-purchase')?.addEventListener('click',()=>$('#purchase-modal').close()); loadMarketplace(); history();
  }
  function fillTrustChoices() {
    const options=state.items.filter(item=>item.available!==false&&item.mode==='₹0 TrustLend'); const select=$('#borrow-item'); if (select) select.innerHTML='<option value="">Choose eligible item…</option>'+options.map(item=>`<option value="${esc(item.id)}">${esc(item.title||item.name)} · Block ${esc(item.hostel_block||item.block||'—')} · owner ${esc(item.owner_name||nameFor(item.owner_id))}</option>`).join('');
  }
  async function loadTrustItems(){try{await loadAllItems();fillTrustChoices();}catch(error){set('#borrow-message',`TrustLend listings unavailable: ${error.message}`);}}
  async function createBorrow(){const item=state.items.find(entry=>String(entry.id)===$('#borrow-item').value); const borrower=$('#borrower-id').value;if(!item||!borrower){message('#borrow-message','Choose an item and borrower first.',true);return;}if(String(item.owner_id)===String(borrower)){message('#borrow-message','Borrower must differ from the listing owner-lender.',true);return;} message('#borrow-message','Creating borrow request…');try{const data=await api('/api/trustlend/borrow',{method:'POST',body:JSON.stringify({item_id:item.id,borrower_id:borrower,lender_id:item.owner_id})});state.request={requestId:data.request_id,token:data.token,item,borrower,lender:item.owner_id,expiresAt:data.expires_at};set('#token-text',data.token||'Token unavailable');$('#scan-input').value='';const qr=$('#qr-code');qr.innerHTML='';if(window.QRCode&&data.token){try{new window.QRCode(qr,{text:data.token,width:150,height:150});}catch{qr.textContent=`QR unavailable. Use token: ${data.token}`;}}else qr.textContent=`QR library unavailable. Use token: ${data.token||'not returned'}`;message('#borrow-message',`Request created. ${nameFor(item.owner_id)} is the lender. Token expires ${new Date(data.expires_at).toLocaleString()}.`);message('#scan-feedback','Camera starts only after selecting Start camera scanner.');}catch(error){message('#borrow-message',`Borrow request failed: ${error.message}`,true);}}
  async function stopScanner(){if(!state.scanner)return;try{await state.scanner.stop();}catch{}try{await state.scanner.clear();}catch{}state.scanner=null;const start=$('#scan-start'),stop=$('#scan-stop');if(start)start.hidden=false;if(stop)stop.hidden=true;}
  async function startScanner(){if(!state.request){message('#scan-feedback','Create a borrow request before scanning.',true);return;}if(!window.Html5Qrcode){message('#scan-feedback','Camera scanner library unavailable. You can enter token or use the labeled demo handover.',true);return;}if(!navigator.mediaDevices?.getUserMedia){message('#scan-feedback','Camera access unavailable in this browser context. Enter the token or use demo handover.',true);return;}try{state.scanner=new window.Html5Qrcode('reader');$('#scan-start').hidden=true;$('#scan-stop').hidden=false;message('#scan-feedback','Requesting camera permission…');await state.scanner.start({facingMode:'environment'},{fps:10,qrbox:{width:200,height:200}},async decoded=>{$('#scan-input').value=decoded;message('#scan-feedback','QR scanned. Confirm token handover to activate loan.');await stopScanner();},()=>{});message('#scan-feedback','Camera active. Align the one-time token QR in frame.');}catch(error){await stopScanner();message('#scan-feedback',`Camera permission denied or scanner failed: ${error.message||'access unavailable'}. Token entry remains available.`,true);}}
  async function handover(simulated){const token=simulated?state.request?.token:$('#scan-input').value.trim();if(!token||!state.request){message('#scan-feedback','Create a borrow request and provide its token first.',true);return;}try{await api('/api/trustlend/handover',{method:'POST',body:JSON.stringify({token})});await stopScanner();state.activeLoan={...state.request,startedAt:new Date().toISOString(),dueAt:new Date(Date.now()+7*86400000).toISOString()};localStorage.setItem('campusloop-active-loan',JSON.stringify(state.activeLoan));set('#scan-feedback',simulated?'Demo handover recorded through the API. No physical handover is verified.':'Token handover recorded through the API.');notify('Loan is active for seven days.');showLoan();loadTrustItems();}catch(error){message('#scan-feedback',`Handover failed: ${error.message}`,true);}}
  function showLoan(){const node=$('#loan-state');if(!node)return;clearInterval(state.countdown);const render=()=>{if(!state.activeLoan){node.textContent='No active loan. Returned loans update persisted trust metrics.';return;}const left=Math.max(0,new Date(state.activeLoan.dueAt).getTime()-Date.now());node.innerHTML=`<div class="loan-row"><strong>${esc(state.activeLoan.item?.title||'Campus item')}</strong><div>Borrower ${esc(nameFor(state.activeLoan.borrower))} · lender ${esc(nameFor(state.activeLoan.lender))}</div><div class="metric">${Math.floor(left/86400000)}d ${Math.floor(left%86400000/3600000)}h ${Math.floor(left%3600000/60000)}m</div><div class="muted">Due ${new Date(state.activeLoan.dueAt).toLocaleString()}</div><button class="btn primary" id="return-loan" type="button">Record return</button></div>`;$('#return-loan')?.addEventListener('click',returnLoan);};render();state.countdown=setInterval(render,60000);}
  async function returnLoan(){if(!state.activeLoan)return;try{const result=await api('/api/trustlend/return',{method:'POST',body:JSON.stringify({token:state.activeLoan.token})});message('#loan-state',`Returned ${new Date(result.returned_at).toLocaleString()}. Borrower trust ${result.borrower_trust_score}; lender trust ${result.lender_trust_score}.`);state.activeLoan=null;state.request=null;localStorage.removeItem('campusloop-active-loan');clearInterval(state.countdown);await Promise.all([loadLeaderboard(),loadLoanHistory()]);loadTrustItems();notify('Return recorded and trust leaderboard refreshed.');}catch(error){notify(`Could not return loan: ${error.message}`,true);}}
  async function loadLoanHistory(){const id=$('#loan-student')?.value;if(!id){set('#loan-history','Choose a demo student to load borrower and lender history.');return;}set('#loan-history','Loading loan history…');try{const data=await api(`/api/trustlend/loans?student_id=${encodeURIComponent(id)}`);const rows=normalizeList(data,'loans');$('#loan-history').innerHTML=rows.length?rows.map(row=>`<div class="loan-row"><strong>${esc(row.item_title||row.title||row.item_id)}</strong><div>Role: ${esc(row.role||'participant')} · ${esc(row.status)}</div><div>Borrower ${esc(row.borrower_name||nameFor(row.borrower_id))} · lender ${esc(row.lender_name||nameFor(row.lender_id))}</div><small class="muted">Started ${esc(row.started_at||'—')} · due ${esc(row.due_at||'—')} · returned ${esc(row.returned_at||'not returned')}</small></div>`).join(''):'<p class="muted">No loan history for this demo student.</p>';}catch(error){set('#loan-history',`Loan history unavailable: ${error.message}`);}}
  async function loadLeaderboard(){try{const data=await api('/api/leaderboard');const rows=normalizeList(data?.blocks??data,'blocks');$('#leaderboard-list').innerHTML=rows.length?rows.map((row,index)=>`<div class="leader"><strong>${index+1}. Block ${esc(row.block)}</strong><div class="muted">${Number(row.on_time_returns||0)} on-time returns · ${Number(row.residents||row.resident_count||0)} residents · trust ${Number(row.trust_score||row.total_trust_score||0)}</div></div>`).join(''):'<p class="muted">No leaderboard data.</p>';message('#leaderboard-error','');}catch(error){$('#leaderboard-list').textContent='Leaderboard unavailable while the API is offline.';message('#leaderboard-error',error.message,true);}}
  function initTrust(){Promise.all([loadStudents(),loadTrustItems()]).then(()=>{$('#borrow-item').value='';$('#borrow-item')?.addEventListener('change',()=>{const item=state.items.find(row=>String(row.id)===$('#borrow-item').value);set('#lender-owner',item?`Lender is the listing owner: ${item.owner_name||nameFor(item.owner_id)} (${item.owner_id}).`:'Choose an item to see its owner-lender.');});loadLoanHistory();});$('#borrow-start')?.addEventListener('click',createBorrow);$('#scan-start')?.addEventListener('click',startScanner);$('#scan-stop')?.addEventListener('click',stopScanner);$('#simulate-handover')?.addEventListener('click',()=>handover(true));$('#confirm-handover')?.addEventListener('click',()=>handover(false));$('#loan-student')?.addEventListener('change',loadLoanHistory);$('#refresh-loans')?.addEventListener('click',loadLoanHistory);$('#refresh-leaderboard')?.addEventListener('click',loadLeaderboard);loadLeaderboard();try{const saved=JSON.parse(localStorage.getItem('campusloop-active-loan')||'null');if(saved?.token&&Date.now()<new Date(saved.dueAt).getTime()){state.activeLoan=saved;showLoan();}}catch{localStorage.removeItem('campusloop-active-loan');}window.addEventListener('pagehide',stopScanner);}
  const stages=[['pickup_scheduled','Hostel Pickup Scheduled'],['pooled','Pooled in Campus Batch'],['auction_won','Wholesale Dealer Auction Won'],['final','Payout Recorded (Simulated)']];
  async function loadPool() {
    try {
      const pool = await api('/api/dealer-pool');
      state.pool = pool;
      const stage = String(pool.stage || 'pickup_scheduled').toLowerCase().replaceAll('-', '_').replaceAll(' ', '_');
      set('#pool-stage-label', stages.find(row => row[0] === stage)?.[1] || stage);
      const index = stages.findIndex(row => row[0] === stage);
      $$('#pipeline .stage').forEach((node, position) => {
        node.classList.toggle('done', position < index);
        node.classList.toggle('active', position === index);
      });
      set('#pool-total', money(pool.pool_estimate));
      set('#scrap-total', money(pool.scrap_estimate));
      const entries = pool.entries || [];
      $('#pool-items').innerHTML = entries.length
        ? `<table class="pool-table"><thead><tr><th>Item</th><th>Owner</th><th>Pool estimate</th><th>Scrap estimate</th></tr></thead><tbody>${entries.map(row => `<tr><td>${esc(row.title || row.item_id)}</td><td>${esc(row.owner_name || nameFor(row.owner_id))}</td><td>${money(row.pool_estimate)}</td><td>${money(row.scrap_estimate)}</td></tr>`).join('')}</tbody></table>`
        : '<div class="empty">No items in this batch yet.</div>';
      const bids = [...(pool.bids || [])].sort((a, b) => Number(b.amount) - Number(a.amount));
      $('#bid-list').innerHTML = bids.length
        ? bids.map((bid, position) => `<tr><td>${esc(bid.dealer_name || bid.dealer_id)}</td><td>${money(bid.amount)}</td><td>${position === 0 ? 'Highest bid' : 'Verified'}</td></tr>`).join('')
        : '<tr><td colspan="3" class="muted">No verified bids yet.</td></tr>';
      if (window.gsap && !document.body.classList.contains('lite') && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        window.gsap.fromTo('#bid-list tr', { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: .25, stagger: .04 });
      }
      $('#payout-box').innerHTML = pool.payouts?.length
        ? `<strong>Simulated payout allocation · no transfer made</strong><br>${pool.payouts.map(row => `Owner ${esc(row.owner_name || nameFor(row.owner_id))}: ${money(row.amount)}`).join('<br>')}${pool.winner ? `<br>Winning dealer: ${esc(pool.winner.dealer_name || pool.winner.dealer_id)} · ${money(pool.winner.amount)}` : ''}`
        : pool.winner
          ? `Winning dealer: ${esc(pool.winner.dealer_name || pool.winner.dealer_id)} · ${money(pool.winner.amount)}. Advance to final for simulated allocations.`
          : 'Allocation is recorded only after the final stage.';
    } catch (error) {
      set('#pool-stage-label', 'API offline');
      $('#pool-items').textContent = `Dealer pool unavailable: ${error.message}`;
    }
  }
  async function initDealer(){await Promise.all([loadStudents().catch(()=>{}),loadAllItems().then(items=>{const select=$('#pool-item');select.innerHTML='<option value="">Choose available listing…</option>'+items.filter(item=>item.available!==false).map(item=>`<option value="${esc(item.id)}">${esc(item.title||item.name)} · ${esc(item.owner_name||nameFor(item.owner_id))}</option>`).join('');}).catch(error=>message('#pool-message',`Listings unavailable: ${error.message}`,true))]);$('#add-pool-item')?.addEventListener('click',async()=>{const itemId=$('#pool-item').value;if(!itemId){message('#pool-message','Choose an available item first.',true);return;}try{await api('/api/dealer-pool/add',{method:'POST',body:JSON.stringify({item_id:itemId})});message('#pool-message','Item added to the active batch.');await loadPool();}catch(error){message('#pool-message',`Could not add item: ${error.message}`,true);}});$('#bid-form')?.addEventListener('submit',async event=>{event.preventDefault();const amount=Number($('#bid-amount').value);if(!Number.isSafeInteger(amount)||amount<1){message('#pool-message','Enter a whole-rupee bid greater than zero.',true);return;}try{await api('/api/dealer-pool/bid',{method:'POST',body:JSON.stringify({dealer_id:$('#dealer-id').value,amount})});$('#bid-amount').value='';message('#pool-message','Verified dealer bid submitted.');await loadPool();}catch(error){message('#pool-message',`Bid rejected: ${error.message}`,true);}});$('#simulate-higher-bid')?.addEventListener('click',async()=>{const highest=Math.max(0,...(state.pool?.bids||[]).map(bid=>Number(bid.amount)||0));const amount=highest+100;try{await api('/api/dealer-pool/bid',{method:'POST',body:JSON.stringify({dealer_id:$('#dealer-id').value,amount})});message('#pool-message',`Demo bid submitted at ${money(amount)}. It is only a simulated bid record.`);await loadPool();}catch(error){message('#pool-message',`Higher demo bid rejected: ${error.message}`,true);}});$('#advance-pool')?.addEventListener('click',async()=>{try{await api('/api/dealer-pool/advance',{method:'POST'});message('#pool-message','Pool advanced exactly one stage.');await loadPool();}catch(error){message('#pool-message',`Cannot advance pool: ${error.message}`,true);}});$('#refresh-pool')?.addEventListener('click',loadPool);loadPool();}
  async function init(){setupPreferences();checkHealth();const page=document.body.dataset.page;if(page==='home')initHome();if(page==='valuation')initValuation();if(page==='marketplace'){try{await loadStudents();}catch(error){set('#market-status',`Student roster unavailable: ${error.message}`);}initMarketplace();}if(page==='trustlend')initTrust();if(page==='dealer')initDealer();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();