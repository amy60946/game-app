using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Pofi.Logic.Island;
using Pofi.Logic.Progression;

public static class Program
{
    public static void Main(string[] args)
    {
        var json = File.ReadAllText(args[0]);
        var map = new IslandMap(json, null);
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var t = new IslandTerrain(map.Regions, map.Terrain);
        Console.WriteLine($"arazi kuruldu: {sw.ElapsedMilliseconds} ms");
        const float step = 0.5f;
        int nx = (int)((t.MaxX - t.MinX) / step) + 1, nz = (int)((t.MaxZ - t.MinZ) / step) + 1;
        var h = new float[nx * nz]; var s = new int[nx * nz];
        for (var j = 0; j < nz; j++) for (var i = 0; i < nx; i++)
        {
            var x = t.MinX + i * step; var z = t.MinZ + j * step;
            h[j * nx + i] = t.Height(x, z); s[j * nx + i] = (int)t.SurfaceAt(x, z);
        }
        Console.WriteLine($"ızgara: {sw.ElapsedMilliseconds} ms");
        var props = t.Props();
        Console.WriteLine($"süsler {props.Count}: {sw.ElapsedMilliseconds} ms");
        var path = t.FindPath(0f, -9f, 20f, 20f);
        Console.WriteLine($"örnek yol {path.Count} nokta: {sw.ElapsedMilliseconds} ms");
        var outp = new
        {
            minX = t.MinX, minZ = t.MinZ, step, nx, nz, h, s,
            regions = map.Regions.Select(r => { var d = t.Door(r); return new { r.Id, r.Name, r.X, r.Z, r.Size, r.Yaw, r.Water, pad = t.PadHeight(r), doorX = d.x, doorZ = d.z }; }),
            props = props.Select(p => new { p.Asset, p.X, p.Z, p.Yaw, p.Size, y = t.Height(p.X, p.Z) }),
            paths = t.Paths.Select(p => new[] { p.ax, p.az, p.bx, p.bz }),
        };
        File.WriteAllText(args[1], JsonConvert.SerializeObject(outp));
    }
}
