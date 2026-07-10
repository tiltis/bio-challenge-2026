(function(){
  var GROUPS=['.tiles','.grid','.plist','.life','.chips','.nav','.sum','.deliver','.prow2','.htabs'];
  var HORIZ=['.tiles','.chips','.nav','.sum','.deliver','.prow2','.htabs','.grid'];
  var on=false, dragEl=null;
  var btn=document.getElementById('mk-edit'),
      save=document.getElementById('mk-save'),
      reset=document.getElementById('mk-reset'),
      hint=document.getElementById('mk-hint');

  function leafText(el){
    if(el.closest('#mk-toolbar,#mk-hint,svg')) return false;
    if(el.children.length===0) return el.textContent.trim().length>0;
    // b/스팬만 품은 짧은 텍스트 요소도 허용
    return Array.prototype.every.call(el.children,function(c){
      return (c.tagName==='B'||c.tagName==='I'||c.tagName==='BR') })
      && el.textContent.trim().length>0;
  }
  function setEdit(v){
    on=v; document.body.classList.toggle('mk-on',v);
    btn.classList.toggle('on',v);
    btn.textContent=v?'✔ 편집 끝내기':'✏️ 편집 모드';
    hint.style.display=v?'block':'none';
    document.querySelectorAll('.wrap *').forEach(function(el){
      if(el.tagName==='SVG'||el.closest('svg'))return;
      if(leafText(el)) v?el.setAttribute('contenteditable','true')
                       :el.removeAttribute('contenteditable');
    });
    GROUPS.forEach(function(sel){
      document.querySelectorAll(sel).forEach(function(box){
        Array.prototype.forEach.call(box.children,function(it){
          it.classList.toggle('mk-item',v);
          if(v){it.setAttribute('draggable','true');}
          else{it.removeAttribute('draggable');}
        });
      });
    });
  }
  btn.onclick=function(){setEdit(!on)};
  reset.onclick=function(){if(confirm('모든 수정을 버리고 처음 상태로 돌아갈까요?'))location.reload()};

  document.addEventListener('dragstart',function(e){
    if(!on)return; var it=e.target.closest('.mk-item'); if(!it)return;
    dragEl=it; setTimeout(function(){it.classList.add('mk-drag')},0);
  });
  document.addEventListener('dragend',function(){ if(dragEl){dragEl.classList.remove('mk-drag'); dragEl=null;} });
  document.addEventListener('dragover',function(e){
    if(!on||!dragEl)return;
    var it=e.target.closest('.mk-item');
    if(!it||it===dragEl||it.parentNode!==dragEl.parentNode)return;
    e.preventDefault();
    var r=it.getBoundingClientRect();
    var horiz=HORIZ.some(function(s){return it.parentNode.matches&&it.parentNode.matches(s)});
    var after=horiz?(e.clientX>r.left+r.width/2):(e.clientY>r.top+r.height/2);
    it.parentNode.insertBefore(dragEl,after?it.nextSibling:it);
  });
  // Alt+클릭 삭제 (카드·아이콘·태그·행)
  document.addEventListener('click',function(e){
    if(!on||!e.altKey)return;
    var it=e.target.closest('.mk-item,.tag,.ins,.chip'); if(!it)return;
    e.preventDefault(); it.remove();
  },true);

  // ── 꾹 눌러 자유 이동 (long-press & drag) ──
  var MOVA='.tile,.gitem,.pcard,.lrow,.chip,.tag,.ins,.risk,.mini-note,.gcard,.guard,'+
           '.sum .s,.deliver button,.htabs span,.nav a,.ribbon,.deck,.cap,.pt-head,'+
           '.role-chip,.brand,.status,.phone,.sec-t,.life,.foot';
  var mvT=null,mvEl=null,sx=0,sy=0,ox=0,oy=0;
  document.addEventListener('pointerdown',function(e){
    if(!on||e.button!==0||e.altKey||e.shiftKey)return;
    var t=e.target.closest(MOVA);
    if(!t||t.closest('#mk-toolbar,#mk-hint'))return;
    sx=e.clientX; sy=e.clientY;
    function cancelMove(ev){ if(Math.hypot(ev.clientX-sx,ev.clientY-sy)>6){clearTimeout(mvT);off();} }
    function offUp(){ clearTimeout(mvT); off(); }
    function off(){ document.removeEventListener('pointermove',cancelMove);
                    document.removeEventListener('pointerup',offUp); }
    mvT=setTimeout(function(){ off(); grab(t); },400);
    document.addEventListener('pointermove',cancelMove);
    document.addEventListener('pointerup',offUp);
  });
  function grab(t){
    mvEl=t;
    var m=/translate\((-?[\d.]+)px,\s*(-?[\d.]+)px\)/.exec(t.style.transform||'');
    ox=m?parseFloat(m[1]):0; oy=m?parseFloat(m[2]):0;
    if(document.activeElement)document.activeElement.blur();
    t.classList.add('mk-moving'); document.body.classList.add('mk-grab');
    t.removeAttribute('draggable');
    function mm(e){ mvEl.style.transform='translate('+(e.clientX-sx+ox)+'px,'+(e.clientY-sy+oy)+'px)'; }
    function mu(){ mvEl.classList.remove('mk-moving'); document.body.classList.remove('mk-grab');
      if(mvEl.classList.contains('mk-item'))mvEl.setAttribute('draggable','true');
      document.removeEventListener('pointermove',mm); document.removeEventListener('pointerup',mu); mvEl=null; }
    document.addEventListener('pointermove',mm);
    document.addEventListener('pointerup',mu);
  }
  // Shift+클릭 = 이동 원상복구
  document.addEventListener('click',function(e){
    if(!on||!e.shiftKey)return;
    var t=e.target.closest(MOVA); if(!t)return;
    e.preventDefault(); t.style.transform='';
  },true);

  save.onclick=function(){
    var was=on; if(was)setEdit(false);
    var root=document.documentElement.cloneNode(true);
    ['#mk-toolbar','#mk-hint'].forEach(function(s){var n=root.querySelector(s);if(n)n.remove();});
    root.querySelectorAll('[contenteditable],[draggable]').forEach(function(n){
      n.removeAttribute('contenteditable');n.removeAttribute('draggable');});
    var html='<meta charset="utf-8">\n'+root.querySelector('body').innerHTML;
    // 스타일은 head가 아니라 body 앞부분에 있으므로 head 쪽도 수거
    var heads=root.querySelectorAll("head>style,head>title,head>link[rel=stylesheet]");
    // 분리 버전: 다운로드한 수정본도 fonts.css/styles.css와 같은 폴더에 두어야 스타일이 적용됩니다
    var pre='';heads.forEach(function(n){pre+=n.outerHTML+'\n'});
    html='<meta charset="utf-8">\n'+pre+root.querySelector('body').innerHTML;
    var a=document.createElement('a');
    a.href=URL.createObjectURL(new Blob([html],{type:'text/html;charset=utf-8'}));
    a.download='앱목업_내수정본.html'; a.click();
    setTimeout(function(){URL.revokeObjectURL(a.href)},2000);
    if(was)setEdit(true);
  };
})();
