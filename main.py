import argparse
import datetime
import re
import os
import tensorflow as tf
from models_code.basic_CNN import BasicCNN as b_cnn
from models_code.basic_MLP import BasicMLP as b_mlp
from models_code.nedo import NEDO
from models_code.vinc import VINC
from models_code.VGG16 import VGG16_19
from utils import config
import time
from utils.generic_utils import print_log
import utils.handle_modes as modes
from utils.preprocessing_data import get_info_dataset
from utils.gradcam_back_code import apply_gradcam


def parse_args():
    parser = argparse.ArgumentParser(
        description='Deep Learning Image-based Malware Classification')
    group = parser.add_argument_group('Arguments')
    # REQUIRED Arguments
    group.add_argument('-m', '--model', required=True, type=str, choices=['DATA', 'BASIC_CNN', 'BASIC_LSTM',
                                                                          'BASIC_MLP', 'NEDO', 'VINC', 'VGG16'],
                       help='Choose the model to use between the ones implemented')
    group.add_argument('-d', '--dataset', required=True, type=str,
                       help='the dataset path, must have the folder structure: training/train, training/val and test,'
                            'in each of this folders, one folder per class (see dataset_test)')
    # OPTIONAL Arguments
    group.add_argument('-o', '--output_model', required=False, type=str, default=None,
                       help='Name of model to store')
    group.add_argument('-l', '--load_model', required=False, type=str, default=None,
                       help='Name of model to load')
    group.add_argument('-t', '--tuning', required=False, type=str, default=None, choices=['hyperband', 'random',
                                                                                          'bayesian'],
                       help='Run Keras Tuner for tuning hyperparameters, options: [hyperband, random, bayesian]')
    group.add_argument('-e', '--epochs', required=False, type=int, default=10,
                       help='number of epochs')
    group.add_argument('-b', '--batch_size', required=False, type=int, default=32)
    group.add_argument('-i', '--image_size', required=False, type=str, default="250x1",
                       help='FORMAT ACCEPTED = SxC , the Size (SIZExSIZE) and channel of the images in input '
                            '(reshape will be applied)')
    group.add_argument('-w', '--weights', required=False, type=str, default=None,
                       help="If you do not want random initialization of the model weights "
                            "(ex. 'imagenet' or path to weights to be loaded), not available for all models!")
    group.add_argument('--mode', required=False, type=str, default='train-val', choices=['train-val', 'train-test',
                                                                                         'test', 'gradcam-cati',
                                                                                         'gradcam-only'],
                       help="Choose which mode run between 'train-val' (default), 'train-test', 'test' or 'gradcam'. "
                            "The 'train-val' mode will run a phase of training and validation on the training and "
                            "validation set, the 'train-test' mode will run a phase of training on the "
                            "training+validation sets and then test on the test set, the 'test' mode will run only a "
                            "phase of test on the test set. The 'gradcam-[cati|only]' will run the gradcam analysis on "
                            "the model provided. 'gradcam-only' will generate the heatmaps only, while 'gradcam-cati "
                            "will also run the cati tool to reverse process and select the code from the heatmap to "
                            "the decompiled smali (if provided, see cati README)")
    # FLAGS
    group.add_argument('--exclude_top', dest='include_top', action='store_false',
                       help='Exclude the fully-connected layer at the top of the network (default INCLUDE)')
    group.set_defaults(include_top=True)
    group.add_argument('--caching', dest='caching', action='store_true',
                       help='Caching dataset on file and loading per batches (IF db too big for memory)')
    group.set_defaults(caching=False)
    arguments = parser.parse_args()
    return arguments


def _check_args(arguments):
    if re.match(r"^\d{2,4}x([13])$", arguments.image_size):
        img_size = arguments.image_size.split("x")[0]
        channels = arguments.image_size.split("x")[1]
        setattr(arguments, "image_size", int(img_size))
        setattr(arguments, "channels", int(channels))
    else:
        print('Invalid image_size, exiting...')
        exit()
    if not os.path.isdir(config.main_path + arguments.dataset):
        print('Cannot find dataset in {}, exiting...'.format(config.main_path + arguments.dataset))
        exit()
    # Check Dataset struct: should be in folder tree training/[train|val] e test
    if not os.path.isdir(config.main_path + arguments.dataset + "/test") or \
            not os.path.isdir(config.main_path + arguments.dataset + "/training/val") or \
            not os.path.isdir(config.main_path + arguments.dataset + "/training/train"):
        print("Dataset '{}' should contain folders 'test, training/train and training/val'...".format(
            arguments.dataset))
        exit()
    if "gradcam-" in arguments.mode and args.load_model is None:
        print("You need to specify a model to load with '-l MODEL_NAME' for the gradcam analysis, exiting...")
        exit()
    if arguments.tuning is not None and arguments.tuning != 'hyperband' and arguments.tuning != 'random' \
            and arguments.tuning != 'bayesian':
        print('Invalid tuning choice, exiting...')
        exit()


def _model_selection(model_choice, nclasses):
    print("INITIALIZING MODEL")
    mod_class = None
    if model_choice == "BASIC_CNN":
        mod_class = b_cnn(nclasses, config.IMG_DIM, config.CHANNELS)
    elif model_choice == "BASIC_MLP":
        mod_class = b_mlp(nclasses, config.VECTOR_DIM)
    elif model_choice == "NEDO":
        mod_class = NEDO(nclasses, config.IMG_DIM, config.CHANNELS)
    elif model_choice == "VINC":
        mod_class = VINC(nclasses, config.IMG_DIM, config.CHANNELS)
    elif model_choice == "VGG16":
        # NB. Setting include_top=True and thus accepting the entire struct, the input Shape MUST be 224x224x3
        # and in any case, channels has to be 3
        if config.CHANNELS != 3:
            print("VGG requires images with channels 3, please set --image_size <YOUR_IMAGE_SIZE>x3, exiting...")
            exit()
        mod_class = VGG16_19(nclasses, config.IMG_DIM, config.CHANNELS) # weights=arguments.weights, include_top=arguments.include_top)
    else:
        print("model {} not implemented yet...".format(model_choice))
        exit()

    return mod_class


if __name__ == '__main__':
    # SET main_path at runtime with the absolute path of the project root folder
    path_list = os.path.realpath(__file__).split("/")[:-1]
    config.main_path = '/'.join(path_list) + '/'

    # START time and parse/check arguments
    start = time.perf_counter()
    args = parse_args()
    _check_args(args)

    # Check info of the dataset
    # STRUCT of class_info = {'class_names': np.array(string), 'n_classes': int,
    # "train_size": int, "val_size": int, "test_size": int, 'info': dict}
    # for name in class_info['class_names'] the info dict contains = {'TRAIN': int, 'VAL': int, 'TEST': int, 'TOT': int}
    class_info, ds_info = get_info_dataset(config.main_path + args.dataset,
                                           update=True if args.model == "DATA" else False)

    # if model set to 'DATA', only updates database info and exit
    if args.model == "DATA":
        print("Dataset info updated, exiting...")
        exit()

    # GLOBAL SETTINGS FOR THE EXECUTIONS
    # Reduce verbosity for Tensorflow Warnings and set dtype for layers
    # tf.keras.backend.set_floatx('float64')
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

    # TODO: checks if we want to perform operation on CPU or GPU
    # os.environ['CUDA_VISIBLE_DEVICES'] = '-1' # to disable GPU
    # Check if tensorflow can access the GPU
    device_name = tf.test.gpu_device_name()
    if not device_name:
        print('GPU device not found...')
    else:
        print('Found GPU at: {}'.format(device_name))

    print_log("STARTING EXECUTION AT\t{}".format(time.strftime("%d-%m %H:%M:%S")), print_on_screen=True)

    config.CHANNELS = args.channels
    config.IMG_DIM = args.image_size
    config.VECTOR_DIM = args.image_size * args.image_size * args.channels

    # SELECTING MODELS
    model_class = _model_selection(args.model, class_info['n_classes'])

    # Initialize variables and logs
    modes.initialization(args, class_info, ds_info, model_class)

    # Special modes
    # If tuning, the model to use has specific architecture define by build_tuning function in model classes
    if args.tuning is not None:
        modes.tuning(args, model_class, ds_info)
    # If gradcam, the model has to be loaded from memory (checked in check_args)
    elif 'gradcam-' in args.mode:
        # the '_loaded' refer to the information on which the model was trained on
        model = modes.load_model(args, required_img=config.IMG_DIM, required_chan=config.CHANNELS,
                                 required_numClasses=class_info['n_classes'])
        apply_gradcam(args, model, class_info, cati=True if args.mode == 'gradcam-cati' else False)

    # Standard modes of training, validation and test
    else:

        # Create model, either load from memory or create from model class
        if args.load_model is not None:
            model = modes.load_model(args, required_img=config.IMG_DIM, required_chan=config.CHANNELS,
                                     required_numClasses=class_info['n_classes'])
        else:
            try:
                model = model_class.build()
            except ValueError as e:
                print("ERROR: {}".format(e))
                print("NB. check if image size is big enough (usually, at least 25x1)")
                exit()

        # Modes which required a training phase
        if args.mode == 'train-val':
            modes.train_val(args, model, ds_info)
        elif args.mode == 'train-test':
            modes.train_test(args, model, class_info, ds_info)
        elif args.mode == 'test':
            modes.test(args, model, class_info, ds_info)

    print_log("ENDING EXECUTION AT\t{}".format(time.strftime("%d-%m %H:%M:%S")), print_on_screen=True)

    end = time.perf_counter()
    print()
    print_log("EX. TIME: {} ".format(str(datetime.timedelta(seconds=end - start))), print_on_screen=True)
