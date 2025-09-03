#!/bin/bash

# Auto-completion script for Augustan Trading CLI
# Source this file or add to your .bashrc/.zshrc

_aug_completion() {
    local cur prev opts cmds
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    # Main commands
    cmds="volume position trading job live config dashboard"
    
    # Subcommands for each main command
    volume_cmds="analyze top"
    position_cmds="analyze tradeable"
    trading_cmds="analyze signals"
    job_cmds="start status"
    live_cmds="start monitor test"
    config_cmds="show init"
    
    # Common options
    common_opts="--help --version --config --verbose"
    
    # If this is the first word, suggest main commands
    if [[ $COMP_CWORD -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${cmds} ${common_opts}" -- "${cur}") )
        return 0
    fi
    
    # Handle subcommands
    case "${prev}" in
        volume)
            COMPREPLY=( $(compgen -W "${volume_cmds}" -- "${cur}") )
            return 0
            ;;
        position)
            COMPREPLY=( $(compgen -W "${position_cmds}" -- "${cur}") )
            return 0
            ;;
        trading)
            COMPREPLY=( $(compgen -W "${trading_cmds}" -- "${cur}") )
            return 0
            ;;
        job)
            COMPREPLY=( $(compgen -W "${job_cmds}" -- "${cur}") )
            return 0
            ;;
        live)
            COMPREPLY=( $(compgen -W "${live_cmds}" -- "${cur}") )
            return 0
            ;;
        config)
            COMPREPLY=( $(compgen -W "${config_cmds}" -- "${cur}") )
            return 0
            ;;
        --config|-c)
            # Complete config files
            COMPREPLY=( $(compgen -f -X "!*.json" -- "${cur}") )
            return 0
            ;;
        --symbol|-s|--symbols)
            # Complete trading symbols
            symbols="BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT ADA/USDT BNB/USDT AVAX/USDT LINK/USDT UNI/USDT DOT/USDT LTC/USDT BCH/USDT XLM/USDT ATOM/USDT NEAR/USDT FTM/USDT ALGO/USDT VET/USDT ICP/USDT"
            COMPREPLY=( $(compgen -W "${symbols}" -- "${cur}") )
            return 0
            ;;
        --exchanges|-e)
            # Complete exchange names
            exchanges="binance"
            COMPREPLY=( $(compgen -W "${exchanges}" -- "${cur}") )
            return 0
            ;;
        --timeframe|-t)
            # Complete timeframes
            timeframes="1m 5m 15m 30m 1h 4h 1d 1w"
            COMPREPLY=( $(compgen -W "${timeframes}" -- "${cur}") )
            return 0
            ;;
        --strategies)
            # Complete strategies
            strategies="rsi macd all"
            COMPREPLY=( $(compgen -W "${strategies}" -- "${cur}") )
            return 0
            ;;
        --type|-t)
            # Complete signal types
            signal_types="buy sell all"
            COMPREPLY=( $(compgen -W "${signal_types}" -- "${cur}") )
            return 0
            ;;
        --strategy|-s)
            # Complete strategies
            strategies="rsi macd all"
            COMPREPLY=( $(compgen -W "${strategies}" -- "${cur}") )
            return 0
            ;;
        --format|-f)
            # Complete output formats
            formats="json csv table"
            COMPREPLY=( $(compgen -W "${formats}" -- "${cur}") )
            return 0
            ;;
        --section|-s)
            # Complete config sections
            sections="risk data signals volume jobs all"
            COMPREPLY=( $(compgen -W "${sections}" -- "${cur}") )
            return 0
            ;;
    esac
    
    # Default completion for options
    if [[ ${cur} == * ]] ; then
        COMPREPLY=( $(compgen -W "${common_opts}" -- "${cur}") )
        return 0
    fi
}

# Register the completion function
complete -F _aug_completion aug

echo "✅ Augustan CLI auto-completion enabled!"
echo "💡 Usage:"
echo "   aug <TAB>                    # Show main commands"
echo "   aug volume <TAB>             # Show volume subcommands"
echo "   aug position analyze --symbol <TAB>  # Show trading symbols"
echo "   aug trading analyze --timeframe <TAB> # Show timeframes"
echo ""
echo "🔧 To enable permanently, add to your ~/.bashrc or ~/.zshrc:"
echo "   source $(pwd)/completion.sh"
