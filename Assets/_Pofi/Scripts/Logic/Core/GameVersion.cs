namespace Pofi.Logic.Core
{
    /// <summary>
    /// Oyun sürümü. Mantık katmanı Unity'ye bağlı değildir; aynı kod hem Unity'de
    /// hem de tests-dotnet altındaki .NET birim testlerinde derlenir.
    /// </summary>
    public static class GameVersion
    {
        public const int Major = 0;
        public const int Minor = 0;
        public const int Patch = 1;
        public const string Milestone = "M0";

        public static string Short => $"{Major}.{Minor}.{Patch}";

        public static string Display(string build) =>
            string.IsNullOrEmpty(build) ? $"v{Short} · {Milestone}" : $"v{Short} · {Milestone} · derleme {build}";
    }
}
