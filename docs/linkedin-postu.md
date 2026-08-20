# LinkedIn paylaşımı — Aktar

> Kopyala-yapıştır için hazır. İlk üç satır kritik: LinkedIn gerisini "daha fazla"
> arkasına saklıyor. Görsel olarak `docs/06-eslestirme-sonucu.png` ekle.

---

Aldığım bir freelance siparişi iptal oldu. Yazılım bitmişti.

Kodu açık kaynak yaptım.

İş şuydu: bir anaokulu, veli aidatlarını devletin paneline elle giriyordu. Ayda 80-130 kayıt, her biri 9-10 tıklama. Yaklaşık iki iş günü, her ay.

Ama asıl zor kısım tıklamak değildi — ekstreyi anlamaktı. Veliler açıklamaya ne isterlerse onu yazıyor:

"Gönd: GAMZE KARTAL Mayıs ayı beren artal 0067-Yapı ve Kredi"

Çocuğun adı bazen başta, bazen sonda, bazen hiç yok — sadece annenin adı var. Soyadın baş harfi düşmüş. "klup / klüp / kulüb", "aidat / aydat". Üstelik aynı soyadlı dört ayrı aile var ve karıştırılmaması gerekiyor.

En çok uğraştığım soru şuydu: program bir eşleşmeye ne zaman "eminim" desin?

Cevap beklediğimden ilginç çıktı. Skor 91 olsa bile, ikinci aday 88'deyse program karar vermiyor — kullanıcıya soruyor. Çünkü aynı soyadlı iki aile varken yüksek skor "doğru" anlamına gelmiyor. Emin olunamayan hiçbir kayıt otomatik girilmiyor.

İkinci detay: bu tür kurumsal panellerin CSS id'leri sürüm değişince kayıyor ve otomasyon sessizce ölüyor. Bu yüzden alanları id'den değil, ekrandaki etiket metninden buluyorum — "Evrak No :" yazan hücrenin yanındaki input.

Bunu yazarken güzel bir tuzağa düştüm: sayfanın tamamını saran bir div de "Evrak No" metnini içerdiği için eşleşiyor ve yanlış alan bulunuyordu. Çözüm, XPath'e "içinde başka element olmayan düğüm" şartı eklemek oldu.

Motor hangi panele girdiğini bilmiyor. Panele özel her şey — adresler, alan etiketleri, ekran akışı — ayrı bir "tarif" dosyasında. Yeni bir panel eklemek, arayüze hiç dokunmadan tek dosya yazmak demek.

Python, Playwright, rapidfuzz, tkinter. 113 test. Windows için exe olarak da indirilebiliyor.

Kod: github.com/ardazeybek-dev/aktar

Not: Depodaki bütün isimler, T.C. numaraları ve banka hareketleri uydurma. Gerçek müşteri verisi yok.

#python #opensource #otomasyon #playwright

---

## Alternatif kısa sürüm (daha çok etkileşim alır)

Bir freelance siparişim iptal oldu. Yazılım bitmişti — açık kaynak yaptım.

Program banka ekstresini okuyup "kim ne ödemiş"i çözüyor, sonra kayıtları web paneline giriyor. Ayda iki iş günü süren bir işi otomatikleştiriyor.

En zor kısmı tıklamak değil, bunu anlamaktı:

"Gönd: GAMZE KARTAL Mayıs ayı beren artal"

Soyadın baş harfi düşmüş, çocuğun adı ortada, aynı soyadlı üç aile daha var.

Öğrendiğim şey: bulanık eşleştirmede asıl mesele skoru yükseltmek değil, ne zaman "emin değilim" diyeceğini bilmek. Skor 91 olsa bile ikinci aday 88'deyse program karar vermiyor, kullanıcıya soruyor.

github.com/ardazeybek-dev/aktar

#python #opensource #otomasyon
