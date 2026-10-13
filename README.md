# Pofi Adası

6–15 yaş için 3D sanal pet oyunu (Unity 6 LTS, URP, iOS + Android). Fidan ebeveyn uygulamasının çocuk tarafı:
çocuk gerçek hayattaki görevini yapar, ebeveyn onaylar, çocuk **coin** kazanır ve adasında pet'ine harcar.

- Plan, mimari, riskler, milestone'lar: [docs/PLAN.md](docs/PLAN.md)
- Unity lisansını GitHub'a tanıtma: [docs/UNITY_LISANS.md](docs/UNITY_LISANS.md)
- Lisanslar: [docs/LICENSES.md](docs/LICENSES.md)

## Durum
**M0 – boru hattı:** Unity projesi koddan kurulur, GitHub Actions ile test edilir ve WebGL önizlemesi üretilir.

## Nasıl çalışır
| Ne | Nerede |
|---|---|
| Oyun mantığı (Unity'siz, birim testli) | `Assets/_Pofi/Scripts/Logic` → `dotnet test tests-dotnet` |
| Unity katmanı | `Assets/_Pofi/Scripts/Runtime` |
| Proje kurulumu + derleme betiği | `Assets/_Pofi/Editor` (`ProjectSetup`, `BuildScript`) |
| Testler | `Assets/Tests/EditMode` |
| CI | `.github/workflows/ci.yml` (mantık testleri → Unity testleri → WebGL önizleme `webgl-preview` dalına; Android APK elle tetiklenir) |
| 3D kaynaklar ve Blender betikleri | `art/` |

### Bilgisayarda açmak (isteğe bağlı)
Unity Hub ile **Unity 6000.3.26f1** kur → **Add project from disk** → bu klasör → menüden **Pofi > Projeyi kur** → `Assets/_Pofi/Scenes/Boot.unity` → Play.
