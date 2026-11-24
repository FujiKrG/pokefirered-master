$ErrorActionPreference = "Stop"

# ---------- 1) Makefile ----------
$path = "Makefile"
$c = [IO.File]::ReadAllText((Resolve-Path $path))

$c = $c -replace 'CPPFLAGS := \$\(INCLUDE_CPP_ARGS\)', 'CPPFLAGS := -std=gnu17 $(INCLUDE_CPP_ARGS)'
$c = $c -replace 'override CFLAGS \+= -mthumb -mthumb-interwork -O\$\(O_LEVEL\)', 'override CFLAGS += -std=gnu17 -mthumb -mthumb-interwork -O$(O_LEVEL)'
$c = $c -replace '(\$\(C_BUILDDIR\)/librfu_intr\.o: CFLAGS := )-mthumb-interwork', '${1}-std=gnu17 -mthumb-interwork'
$c = $c -replace 'CPP := \$\(PREFIX\)cpp(?! -std=gnu17)', 'CPP := $(PREFIX)cpp -std=gnu17'

[IO.File]::WriteAllText((Resolve-Path $path), $c)

# ---------- 2) rematches.h ----------
$path = "include/constants/rematches.h"
$c = [IO.File]::ReadAllText((Resolve-Path $path))
$c = $c -replace '(?m)^\s*REMATCH_NONE\s*=\s*0\s*,\s*\r?\n?', ''
[IO.File]::WriteAllText((Resolve-Path $path), $c)

# ---------- 3) field_player_avatar.c ----------
$path = "src/field_player_avatar.c"
$c = [IO.File]::ReadAllText((Resolve-Path $path))
$c = $c -replace 'static u8 ObjectEventCB2_NoMovement2\(\);', 'static bool8 ObjectEventCB2_NoMovement2(struct ObjectEvent *, struct Sprite *);'
$c = $c -replace 'static u8 ObjectEventCB2_NoMovement2\(void\)', 'static bool8 ObjectEventCB2_NoMovement2(struct ObjectEvent *objectEvent, struct Sprite *sprite)'
[IO.File]::WriteAllText((Resolve-Path $path), $c)

# ---------- 4) limpar e compilar ----------
Write-Host ""
Write-Host "=== Arquivos corrigidos. Limpando e compilando... ==="
make tidy
make modern -j