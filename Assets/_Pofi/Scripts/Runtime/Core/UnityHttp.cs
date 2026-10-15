using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Pofi.Logic.Services.Supabase;
using UnityEngine.Networking;

namespace Pofi.Core
{
    /// <summary>Supabase istemcisi için HTTP (UnityWebRequest; WebGL'de tarayıcının fetch'i). Ağ hatasında Status = 0.</summary>
    public sealed class UnityHttp : IHttp
    {
        public int TimeoutSeconds = 15;

        public Task<HttpReply> SendAsync(string method, string url, IDictionary<string, string> headers, string body, CancellationToken ct)
        {
            var tcs = new TaskCompletionSource<HttpReply>();
            var req = new UnityWebRequest(url, method) { downloadHandler = new DownloadHandlerBuffer(), timeout = TimeoutSeconds };
            if (body != null) req.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(body));
            if (headers != null)
                foreach (var h in headers) req.SetRequestHeader(h.Key, h.Value);
            var reg = ct.CanBeCanceled ? ct.Register(() => { if (!tcs.Task.IsCompleted) req.Abort(); }) : default;
            req.SendWebRequest().completed += _ =>
            {
                var code = (int)req.responseCode;
                var failed = req.result == UnityWebRequest.Result.ConnectionError || req.result == UnityWebRequest.Result.DataProcessingError;
                var reply = new HttpReply { Status = failed || code == 0 ? 0 : code, Body = req.downloadHandler != null ? req.downloadHandler.text : null };
                reg.Dispose();
                req.Dispose();
                tcs.TrySetResult(reply);
            };
            return tcs.Task;
        }
    }
}
