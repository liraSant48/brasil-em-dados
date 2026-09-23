param([string]$Definition = "$PSScriptRoot/../powerbi/Brasil_em_Dados.SemanticModel/definition")
$ErrorActionPreference = 'Stop'
$pbiBin = (Get-AppxPackage *PowerBI* | Select-Object -First 1).InstallLocation + '/bin'
foreach ($name in @('Microsoft.AnalysisServices.Server.Tabular.dll', 'Microsoft.PowerBI.Amo.dll', 'Microsoft.PowerBI.Tabular.dll')) {
    [void][Reflection.Assembly]::LoadFrom("$pbiBin/$name")
}
# Desserializa sem salvar o modelo ou conectar ao mecanismo DAX.
$database = [Microsoft.AnalysisServices.Tabular.TmdlSerializer]::DeserializeDatabaseFromFolder((Resolve-Path $Definition).Path)
$table = $database.Model.Tables['despesas_bi']
if (-not $table) { throw 'Tabela despesas_bi ausente.' }
$expected = @{
    'Total Pago' = "SUM('despesas_bi'[valor_pago])"
    'Total Empenhado' = "SUM('despesas_bi'[valor_empenhado])"
    'Total Liquidado' = "SUM('despesas_bi'[valor_liquidado])"
    'Restos a Pagar Pagos' = "SUM('despesas_bi'[valor_restos_pagos])"
    'Quantidade de Registros' = "COUNTROWS('despesas_bi')"
}
foreach ($name in $expected.Keys) {
    if ($table.Measures[$name].Expression.Trim() -ne $expected[$name]) { throw "Medida divergente: $name" }
}
Write-Output "TMDL desserializado: $($database.Model.Tables.Count) tabelas; 5 medidas conferidas. Nenhum arquivo alterado."
