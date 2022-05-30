function RunBot
{
    conda activate reddit-function-bot
    func start --functions start poll reply post manager tag --port 7071
}


Do {
  RunBot
} while(1 == 1)