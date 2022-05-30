function RunBot {
    conda activate reddit-function-bot
    func start --functions gen --port 7073
}

RunBot

if (!$LastExitCode) {
        RunBot
}
else{
    RunBot
}