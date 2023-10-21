#!/usr/bin/env python3
import sys
import argparse
import logging

from .log import LogFormatter


class ArgParser(argparse.ArgumentParser):
    """
    Adds selectable extra args that are commonly used by this project
    """
    DefaultExtras = ['model', 'chat', 'generation', 'log']
    Video = ['video_input', 'video_output']
    Riva = ['asr', 'tts']
    
    def __init__(self, extras=DefaultExtras, **kwargs):
        super().__init__(formatter_class=argparse.ArgumentDefaultsHelpFormatter, **kwargs)
        
        if 'model' in extras:
            self.add_argument("--model", type=str, required=True, 
                help="path to the model, or repository on HuggingFace Hub")
            self.add_argument("--quant", type=str, default=None, 
                help="path to the quantized weights (AWQ uses this)")
            self.add_argument("--api", type=str, default=None, choices=['auto_gptq', 'awq', 'hf', 'mlc'], 
                help="specify the API to use (otherwise inferred)")
            self.add_argument("--vision-model", type=str, default=None, 
                help="for VLMs, manually select the CLIP vision model to use (e.g. openai/clip-vit-large-patch14-336 for higher-res)")

        if 'chat' in extras:
            self.add_argument("--prompt", action='append', nargs='*', 
                help="add a prompt (can be prompt text or path to .txt, .json, or image file)")
            self.add_argument("--system-prompt", type=str, default=None, help="override the system prompt instruction")
            self.add_argument("--chat-template", type=str, default=None, #choices=list(ChatTemplates.keys()), 
                help="manually select the chat template ('llama-2', 'llava-v1', 'vicuna-v1')")

        if 'generation' in extras:
            self.add_argument("--max-new-tokens", type=int, default=128, 
                help="the maximum number of new tokens to generate, in addition to the prompt")
            self.add_argument("--min-new-tokens", type=int, default=-1,
                help="force the model to generate a minimum number of output tokens")
            self.add_argument("--do-sample", action="store_true",
                help="enable output token sampling using temperature and top_p")
            self.add_argument("--temperature", type=float, default=0.7,
                help="token sampling temperature setting when --do-sample is used")
            self.add_argument("--top-p", type=float, default=0.95,
                help="token sampling top_p setting when --do-sample is used")
            self.add_argument("--repetition-penalty", type=float, default=1.0,
                help="the parameter for repetition penalty. 1.0 means no penalty")

        if 'video_input' in extras:
            self.add_argument("--video-input", type=str, default=None, help="video camera device name, stream URL, file/dir path")
            self.add_argument("--video-input-width", type=int, default=None, help="manually set the resolution of the video input")
            self.add_argument("--video-input-height", type=int, default=None, help="manually set the resolution of the video input")
            self.add_argument("--video-input-codec", type=str, default=None, choices=['h264', 'h265', 'vp8', 'vp9', 'mjpeg'], help="manually set the input video codec to use")
            self.add_argument("--video-input-framerate", type=int, default=None, help="set the desired framerate of input video")
            
        if 'video_output' in extras:
            self.add_argument("--video-output", type=str, default=None, help="display, stream URL, file/dir path")
            self.add_argument("--video-output-codec", type=str, default=None, choices=['h264', 'h265', 'vp8', 'vp9', 'mjpeg'], help="set the output video codec to use")
            self.add_argument("--video-output-bitrate", type=int, default=None, help="set the output bitrate to use")
          
                    
        if 'asr' in extras or 'tts' in extras:
            self.add_argument("--riva-server", default="localhost:50051", help="URI to the Riva GRPC server endpoint.")
            self.add_argument("--sample-rate-hz", default=48000, help="the audio sample rate in Hz")
            self.add_argument("--language-code", default="en-US", help="Language code of the ASR/TTS to be used.")
            
        if 'tts' in extras:
            self.add_argument("--voice", type=str, default="English-US.Female-1", help="Voice model name to use for TTS")

        if 'asr' in extras:
            self.add_argument("--list-audio-devices", action="store_true", help="List output audio devices indices.")
            self.add_argument("--audio-input", type=int, default=None, help="audio input device/microphone to use for ASR")
            self.add_argument("--audio-chunk", type=int, default=1600, help="A maximum number of frames in a audio chunk sent to server.")
            self.add_argument("--audio-channels", type=int, default=1, help="The number of audio channels to use")
            self.add_argument("--boosted-lm-words", action='append', help="Words to boost when decoding.")
            self.add_argument("--boosted-lm-score", type=float, default=4.0, help="Value by which to boost words when decoding.")
            self.add_argument("--profanity-filter", action='store_true', help="enable profanity filtering in ASR transcripts")
            self.add_argument("--no-automatic-punctuation", dest='automatic_punctuation', action='store_false', help="disable punctuation in the ASR transcripts")

        if 'log' in extras:
            self.add_argument("--log-level", type=str, default='info', choices=['debug', 'info', 'warning', 'error', 'critical'], help="the logging level to stdout")
            self.add_argument("--debug", "--verbose", action="store_true", help="set the logging level to debug/verbose mode")
                
    def parse_args(self, **kwargs):
        """
        Override for parse_args() that does some additional configuration
        """
        args = super().parse_args(**kwargs)
        
        if hasattr(args, 'prompt'):
            args.prompt = ArgParser.parse_prompt_args(args.prompt)
        
        if hasattr(args, 'log_level'):
            if args.debug:
                args.log_level = "debug"
            LogFormatter.config(level=args.log_level)
            
        if hasattr(args, 'list_audio_devices') and args.list_audio_devices:
            import riva.client
            riva.client.audio_io.list_output_devices()
            sys.exit(0)
            
        logging.debug(f"{args}")
        return args
        
    @staticmethod
    def parse_prompt_args(prompts, chat=True):
        """
        Parse prompt command-line argument and return list of prompts
        It's assumed that the argparse argument was created like this:
        
          `parser.add_argument('--prompt', action='append', nargs='*')`
          
        If the prompt text is 'default', then default chat prompts will
        be assigned if chat=True (otherwise default completion prompts)
        """
        if prompts is None:
            return None
            
        prompts = [x[0] for x in prompts]
        
        if prompts[0].lower() == 'default' or prompts[0].lower() == 'defaults':
            prompts = DefaultChatPrompts if chat else DefaultCompletionPrompts
            
        return prompts
        