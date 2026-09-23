param(
    [string]$Candidate = "$PSScriptRoot/../data/processed/pbir_overview_candidate",
    [string]$Schemas = "$PSScriptRoot/../data/processed/pbir_local_schemas"
)
$ErrorActionPreference = 'Stop'
$pbiBin = (Get-AppxPackage *PowerBI* | Select-Object -First 1).InstallLocation + '/bin'
$jsonAssembly = [Reflection.Assembly]::LoadFrom("$pbiBin/Newtonsoft.Json.dll")
[AppDomain]::CurrentDomain.add_AssemblyResolve({
    param($sender, $eventArgs)
    if ($eventArgs.Name.StartsWith('Newtonsoft.Json,')) { return $jsonAssembly }
})
$schemaAssembly = [Reflection.Assembly]::LoadFrom("$pbiBin/Newtonsoft.Json.Schema.dll")
# PreloadedResolver não consulta a rede; todas as referências vêm do Desktop local.
$resolver = [Newtonsoft.Json.Schema.JSchemaPreloadedResolver]::new()
$schemaTexts = @{}
Get-ChildItem -LiteralPath "$Schemas/bundled" -Filter '*.json' | ForEach-Object {
    $body = [IO.File]::ReadAllText($_.FullName)
    $data = ConvertFrom-Json $body
    if ($data.'$id' -and -not $schemaTexts.ContainsKey($data.'$id')) {
        $schemaTexts[$data.'$id'] = $body
        $resolver.Add([Uri]$data.'$id', $body)
    }
}
$settings = [Newtonsoft.Json.Schema.JSchemaReaderSettings]::new()
$settings.Resolver = $resolver
$validated = 0
function Get-SchemaErrors($items) {
    foreach ($item in $items) {
        "$($item.Path): $($item.Message)"
        Get-SchemaErrors $item.ChildErrors
    }
}
Get-ChildItem -LiteralPath $Candidate -Recurse -Filter '*.json' | ForEach-Object {
    $body = [IO.File]::ReadAllText($_.FullName)
    $data = ConvertFrom-Json $body
    if ($data.'$schema') {
        if (-not $schemaTexts.ContainsKey($data.'$schema')) { throw "Esquema local ausente: $($data.'$schema')" }
        $schema = [Newtonsoft.Json.Schema.JSchema]::Parse($schemaTexts[$data.'$schema'], $settings)
        $token = [Newtonsoft.Json.Linq.JToken]::Parse($body)
        $errors = [System.Collections.Generic.IList[Newtonsoft.Json.Schema.ValidationError]]([System.Collections.Generic.List[Newtonsoft.Json.Schema.ValidationError]]::new())
        if (-not [Newtonsoft.Json.Schema.SchemaExtensions]::IsValid($token, $schema, [ref]$errors)) {
            throw "$($_.FullName): $((Get-SchemaErrors $errors) -join ' | ')"
        }
        $validated += 1
    }
}
Write-Output "Arquivos aprovados nos esquemas oficiais locais: $validated"
