# LinkedIn paylaşımı — Aktar

> Kopyala-yapıştır için hazır. Görsel: `docs/06-eslestirme-sonucu.png`
> (masaüstünde `Aktar-linkedin-gorsel.png` olarak da duruyor).
> İlk üç satır kritik — LinkedIn gerisini "daha fazla" arkasına saklıyor.

---

## English

I built a Windows desktop application and open-sourced it: **Aktar**.

It reads a bank statement, works out who paid what, and enters the records into a web panel for you.

The problem it solves is boring and expensive. An organisation that receives a hundred-odd transfers a month — a school, an association, a building management office, a small accounting practice — has to type every single one of them into some web panel by hand. Nine or ten clicks per record. Days of work, every month, forever.

The hard part is not the clicking. It is reading the statement. People write whatever they like in the transfer description: sometimes the payer's name, sometimes the child's, sometimes both, sometimes neither. A surname arrives missing its first letter. Four different families share one surname and must not be confused with each other. Mixed in are payments that are not fees at all and must never be entered.

What Aktar does:

→ **Reads the statement** — finds the header row on its own, parses Turkish number format (-22.936,29), discards the bank's letterhead and footnotes, and recovers Excel files that openpyxl refuses to open at all

→ **Matches every payment to a person** — Turkish-aware fuzzy matching, then rules each row certain / uncertain / none

→ **Enters the records into the panel** — Playwright, one record at a time, skipping and reporting anything that fails instead of dying halfway

Two decisions I am happy with:

**1. Precision over coverage.** Even at a match score of 91, if the runner-up sits at 88 the program refuses to decide and asks the user instead. When two families share a surname, a high score does not mean correct. A wrongly attributed payment costs far more than one a human confirms by hand.

**2. Fields are found by their label text, not by element id.** Legacy ASP.NET panels shift their ids between releases and automation dies silently. Aktar looks for the input next to the cell that reads "Evrak No :" instead. The subtle part: you have to require a leaf node, otherwise the div wrapping the whole page also contains that text and you fill the wrong field.

**Architecture:** the engine does not know the panel. Everything panel-specific — addresses, field labels, screen flow — lives in a separate *recipe* file. Adding a new panel means writing one file and touching no UI code at all.

**No credentials are stored.** The user signs in themselves, the program waits, then enters the user's own data in the user's own session. Nothing leaves the machine.

Python · Playwright · rapidfuzz · tkinter · 113 tests · MIT licensed

Source: github.com/ardazeybek-dev/aktar

#python #opensource #automation #playwright #softwareengineering

---

## Türkçe

Bir Windows masaüstü uygulaması yazdım ve açık kaynak yaptım: **Aktar**.

Banka ekstresini okuyor, kimin ne ödediğini çözüyor ve kayıtları web paneline sizin yerinize giriyor.

Çözdüğü problem sıkıcı ve pahalı. Ayda yüz küsur havale alan bir kurum — okul, dernek, apartman yönetimi, küçük bir muhasebe bürosu — bunların her birini bir web paneline elle girmek zorunda. Kayıt başına dokuz on tıklama. Her ay, günlerce süren bir iş.

Zor kısım tıklamak değil. Ekstreyi okumak. İnsanlar açıklamaya ne isterlerse onu yazıyor: bazen ödeyenin adı, bazen çocuğun, bazen ikisi, bazen hiçbiri. Soyadın baş harfi düşüyor. Aynı soyadı taşıyan dört ayrı aile var ve karıştırılmaması gerekiyor. Arada aidat olmayan ödemeler var, onların hiç girilmemesi gerekiyor.

Aktar ne yapıyor:

→ **Ekstreyi okuyor** — başlık satırını kendi buluyor, Türkçe sayı formatını (-22.936,29) anlıyor, banka antetini ve dipnotlarını atıyor, openpyxl'in hiç açamadığı bozuk Excel dosyalarını kurtarıyor

→ **Her ödemeyi bir kişiyle eşleştiriyor** — Türkçeye özel bulanık eşleştirme, sonra her satıra kesin / şüpheli / yok kararı

→ **Kayıtları panele giriyor** — Playwright ile, tek tek; bir kayıt patlarsa yarı yolda ölmüyor, o satırı atlayıp raporluyor

Memnun olduğum iki karar:

**1. Kapsamdan çok isabet.** Eşleşme skoru 91 olsa bile, ikinci aday 88'deyse program karar vermiyor, kullanıcıya soruyor. Aynı soyadlı iki aile varken yüksek skor "doğru" demek değil. Yanlış atanan bir ödeme, kullanıcının elle onayladığı ödemeden çok daha pahalıya patlıyor.

**2. Alanlar element id'siyle değil, ekrandaki etiket metniyle bulunuyor.** Eski ASP.NET panellerinin id'leri sürüm değişince kayıyor ve otomasyon sessizce ölüyor. Aktar bunun yerine "Evrak No :" yazan hücrenin yanındaki input'u arıyor. İnce nokta: yaprak düğüm şartı koymak zorundasınız, yoksa sayfanın tamamını saran div de o metni içeriyor ve yanlış alanı dolduruyorsunuz.

**Mimari:** motor hangi panele girdiğini bilmiyor. Panele özel her şey — adresler, alan etiketleri, ekran akışı — ayrı bir *tarif* dosyasında. Yeni bir panel eklemek, arayüze hiç dokunmadan tek dosya yazmak demek.

**Hiçbir şifre saklanmıyor.** Girişi kullanıcı kendisi yapıyor, program bekliyor, sonra kullanıcının kendi verisini kendi oturumunda giriyor. Hiçbir veri bilgisayardan çıkmıyor.

Python · Playwright · rapidfuzz · tkinter · 113 test · MIT lisansı

Kaynak kod: github.com/ardazeybek-dev/aktar

#python #açıkkaynak #otomasyon #playwright #yazılım
