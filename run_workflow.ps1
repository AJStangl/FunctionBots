function RunBot {
    conda activate reddit-function-bot
    func start --functions generate -p 7072
}

RunBot

if (!$LastExitCode) {
        RunBot
}
else{
    RunBot
}