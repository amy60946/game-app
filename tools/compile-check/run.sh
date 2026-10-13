#!/usr/bin/env bash
# Unity olmadan Runtime katmanının (Pofi.Runtime) C# derleme denetimi.
# NuGet'teki Unity başvuru derlemeleriyle (2021.3 modülleri + UGUI 2020.3) derler: API'lerin çoğu Unity 6 ile aynıdır,
# ama bu yalnızca hızlı bir ön kontrol; kesin doğrulama CI'daki GameCI derlemesidir.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
ref="${UNITY_REF_DIR:-$here/.ref}"
mkdir -p "$ref"
get() { # paket sürüm
  [ -d "$ref/$1" ] && return
  curl -sfL -o "$ref/$1.nupkg" "https://api.nuget.org/v3-flatcontainer/$1/$2/$1.$2.nupkg"
  unzip -oq "$ref/$1.nupkg" -d "$ref/$1"
}
get unityengine.modules 2021.3.33
get unity3d.unityengine.ui 2020.3.21
dotnet build "$here/RuntimeCheck.csproj" -nologo -v q -p:UnityRef="$ref" "$@"
