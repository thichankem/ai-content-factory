$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8080"
$topics = @(
    "World War I: the Western Front",
    "World War II: the Battle of Stalingrad",
    "Vietnam War: the Ho Chi Minh trail",
    "Korean War: the Pusan Perimeter",
    "Peloponnesian War: Athens and Sparta",
    "Hundred Years' War: England and France",
    "Napoleonic Wars: the Battle of Waterloo",
    "Crimean War: the Siege of Sevastopol",
    "Punic Wars: Rome and Carthage",
    "American Revolutionary War: Saratoga"
)
$scriptText = @"
[Hook]
A war is decided not only by gunfire, but by logistics, terrain, and human choices.
[Context]
This episode establishes the historical setting, the combatants, their strategic aims, and the civilians affected by the conflict.
[Turn]
When the battlefield changes, the first plan is no longer enough. Commanders must adapt to incomplete information, weather, terrain, and political pressure.
[Evidence]
Historical sources show that outcomes rarely come from one moment. They emerge from a chain of decisions, mistakes, and endurance.
[Human]
Behind every map are soldiers, families, and communities carrying the cost of war. Their story must be told accurately and respectfully.
[Payoff]
The central lesson is that victory on paper cannot erase the human price, and history is shaped by specific choices.
[CTA]
Keep checking sources, listen to more than one perspective, and remember that understanding war is meant to protect peace.
"@

function Invoke-Json($method, $path, $body) {
    $json = $body | ConvertTo-Json -Depth 12
    return Invoke-RestMethod -Method $method -Uri "$base$path" -ContentType "application/json" -Body $json
}

$results = [System.Collections.Generic.List[object]]::new()
for ($index = 0; $index -lt $topics.Count; $index++) {
    $topic = $topics[$index]
    $name = "War QA $($index + 1)"
    $projectId = ""
    try {
        $project = Invoke-Json POST "/projects" @{
            name = $name
            topic = $topic
            target_language = "en"
            duration_target_seconds = 300
        }
        $projectId = $project.id
        if ($project.status -ne "draft" -or $project.duration_target_seconds -ne 300) {
            throw "create invariant failed"
        }

        $project = Invoke-Json PUT "/projects/$projectId/script" @{
            script = $scriptText
            source_rights_confirmed = $true
        }
        if ($project.status -ne "script_review" -or -not $project.source_rights_confirmed) {
            throw "script review preparation failed"
        }

        $project = Invoke-Json POST "/projects/$projectId/approvals" @{
            stage = "script"
            verdict = "approved"
            comment = "Human QA approval"
        }
        if ($project.status -ne "script_approved") {
            throw "script approval failed"
        }

        $project = Invoke-Json POST "/projects/$projectId/generate" @{}
        if ($project.status -ne "generating") {
            throw "generation start failed"
        }

        $deadline = (Get-Date).AddSeconds(30)
        do {
            Start-Sleep -Milliseconds 200
            $project = Invoke-RestMethod -Method Get -Uri "$base/projects/$projectId"
        } while ($project.status -eq "generating" -and (Get-Date) -lt $deadline)
        if ($project.status -ne "video_review") {
            throw "generation ended in $($project.status)"
        }
        if ($project.progress -ne 100 -or $project.video.duration_seconds -lt 300) {
            throw "video metadata invariant failed"
        }

        $timeline = Invoke-RestMethod -Method Get -Uri "$base/projects/$projectId/video-project"
        $timelineDuration = ($timeline.scenes | Measure-Object -Property duration_seconds -Sum).Sum
        if ($timelineDuration -lt 299.99 -or $timeline.scenes.Count -lt 1) {
            throw "timeline invariant failed"
        }

        $project = Invoke-Json POST "/projects/$projectId/approvals" @{
            stage = "video"
            verdict = "approved"
            comment = "Human final video QA approval"
        }
        if ($project.status -ne "video_approved") {
            throw "video approval failed"
        }

        $project = Invoke-Json POST "/projects/$projectId/publish" @{ platforms = @("youtube", "tiktok") }
        if ($project.status -ne "published") {
            throw "publish failed"
        }

        $results.Add([pscustomobject]@{
            index = $index + 1
            id = $projectId
            topic = $topic
            status = $project.status
            duration = $project.video.duration_seconds
            timeline_duration = $timelineDuration
            scenes = $timeline.scenes.Count
            asset_url = $project.video.asset_url
        })
        Write-Output "PASS $name | $projectId | $($project.video.duration_seconds)s | $($timeline.scenes.Count) scenes | published"
    } catch {
        $results.Add([pscustomobject]@{
            index = $index + 1
            id = $projectId
            topic = $topic
            status = "failed"
            duration = 0
            scenes = 0
            asset_url = $_.Exception.Message
        })
        Write-Output "FAIL $name | $topic | $($_.Exception.Message)"
    }
}

$passed = @($results | Where-Object { $_.status -eq "published" }).Count
$failed = $results.Count - $passed
Write-Output "SUMMARY total=$($results.Count) passed=$passed failed=$failed"
$results | ConvertTo-Json -Depth 5
if ($failed -gt 0) {
    exit 1
}