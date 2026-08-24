/* ============================================================
   Sahte supabase-js — YALNIZ TEST icin. app/ icinde DEGIL, yayina cikmaz.

   NEDEN VAR: test_sayfa.py butun dis baglantilari kesiyor (bilerek: zor
   hal sinansin). Yan etkisi, supabase-js'in hicbir zaman gelmemesiydi --
   yani GIRIS YAPILMIS halin hicbir sayfasi gercek tarayicida hic
   calistirilmadi. hesabim.html'in dort listesi, yonetim.html'in onay
   dugmeleri, isletme.html'in fis ve sahiplik katmanlari: hepsi yalnizca
   elle acilarak gorulmustu.

   Burasi kimlik.js'in KULLANDIGI yuzeyi taklit ediyor, Supabase'in
   tamamini degil. Yetki taklit EDILMIYOR: RLS'in dogru oldugu gercek
   Postgres'te sinaniyor (veritabani/kos.sh). Burada sinanan sey ARAYUZ --
   veri gelince ekranda dogru sey cikiyor mu.
   ============================================================ */
const V = globalThis.__SAHTE_VERI || { oturum: null, profil: null, tablolar: {}, rpc: {} };

function suz(satirlar, kosullar){
  return satirlar.filter(r => kosullar.every(([k, d]) => String(r[k]) === String(d)));
}

function sorgu(tablo){
  const durum = { kosul: [], sira: null, artan: true, limit: null, tek: false };
  const calistir = () => {
    let l = (V.tablolar[tablo] || []).slice();
    l = suz(l, durum.kosul);
    if (durum.sira) l.sort((a, b) => {
      const x = a[durum.sira], y = b[durum.sira];
      return (x < y ? -1 : x > y ? 1 : 0) * (durum.artan ? 1 : -1);
    });
    if (durum.limit != null) l = l.slice(0, durum.limit);
    return durum.tek ? { data: l[0] || null, error: null } : { data: l, error: null };
  };
  const z = {
    select(){ return z; },
    eq(k, d){ durum.kosul.push([k, d]); return z; },
    order(k, o){ durum.sira = k; durum.artan = !(o && o.ascending === false); return z; },
    limit(n){ durum.limit = n; return z; },
    maybeSingle(){ durum.tek = true; return Promise.resolve(calistir()); },
    single(){ durum.tek = true; return Promise.resolve(calistir()); },
    insert(satir){
      const l = V.tablolar[tablo] || (V.tablolar[tablo] = []);
      for (const r of [].concat(satir)) l.push(Object.assign({ id: l.length + 1 }, r));
      return Promise.resolve({ data: null, error: null });
    },
    update(yama){
      return { eq(k, d){
        suz(V.tablolar[tablo] || [], [[k, d]]).forEach(r => Object.assign(r, yama));
        return Promise.resolve({ data: null, error: null });
      } };
    },
    delete(){
      return { eq(k, d){
        V.tablolar[tablo] = (V.tablolar[tablo] || []).filter(r => String(r[k]) !== String(d));
        return Promise.resolve({ data: null, error: null });
      } };
    },
    then(c, h){ return Promise.resolve(calistir()).then(c, h); }
  };
  return z;
}

/* Depolama taklidi. Gercek istemcide sb.storage var ve kimlik.js onu
   avatar ile menu fotografi icin kullaniyor; taklitte olmayinca sayfa
   "Cannot read properties of undefined (reading 'from')" ile catliyordu.
   Dosya GERCEKTEN saklanmiyor -- burada sinanan sey arayuz. */
function depo(kova){
  return {
    upload(yol){
      (V.dosyalar || (V.dosyalar = [])).push({ kova, yol });
      return Promise.resolve({ data: { path: yol }, error: null });
    },
    remove(yollar){
      V.dosyalar = (V.dosyalar || []).filter(d => !yollar.includes(d.yol));
      return Promise.resolve({ data: null, error: null });
    },
    getPublicUrl(yol){
      return { data: { publicUrl: "https://ornek.test/" + kova + "/" + yol } };
    }
  };
}

export function createClient(){
  return {
    from: sorgu,
    storage: { from: depo },
    rpc(ad, p){
      const f = V.rpc[ad];
      return Promise.resolve(f ? f(p) : { data: null, error: { message: "rpc yok: " + ad } });
    },
    auth: {
      getSession: () => Promise.resolve({ data: { session: V.oturum }, error: null }),
      onAuthStateChange(){ return { data: { subscription: { unsubscribe(){} } } }; },
      signUp: () => Promise.resolve({ data: { session: null }, error: null }),
      signInWithPassword: () => Promise.resolve({ data: {}, error: null }),
      signOut: () => { V.oturum = null; return Promise.resolve({ error: null }); },
      resetPasswordForEmail: () => Promise.resolve({ error: null }),
      updateUser: () => Promise.resolve({ error: null })
    }
  };
}
export default { createClient };
