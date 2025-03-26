from preprocessor.preprocess import Preprocessor
from postprocessor.postprocess import Postprocessor
from classifier.inference import inference
from classifier.train import train
from omegaconf import DictConfig
from omegaconf import OmegaConf
from pathlib import Path
import uuid
import os
import logging
import hydra

logger = logging.getLogger(__name__)
class Pipeline:
    """
    Pipeline class handles all the operations related to C-brain.
    
    Currently Pipeline supports two major methods-
    run_cbrain(): This method initiates entire cbrain composed of preprocessing, inference, and post processing pipelines.
    run_cbrain_training(): This method initiates cbrain training and is composed of preprocessing and training pipelines.
    
    start_preprocess(), start_inference(), and start_training() can be invoked as standalone methods
    """

    def __init__(self, cfg: DictConfig):

        # Generate Universally Unique Identifier for every instance of Pipeline class to have unique directory to store artifacts.
        self.uuid = uuid.uuid4()

        # Extract runtime output directory to store final output, logs, and intermediate files.
        self.output_dir =os.path.join(hydra.core.hydra_config.HydraConfig.get()['runtime']['output_dir'],  str(self.uuid))

        # Create logs directory
        log_path = os.path.join(self.output_dir , "logs")
        os.makedirs(log_path)
        logging.basicConfig(
            level=logging.INFO,  
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  
            handlers=[
                logging.FileHandler(str(os.path.join(log_path, "cbrain.log"))), 
                logging.StreamHandler()         
        ]
    )
        #Contains all the data from hydra configs
        self.cfg = OmegaConf.to_container(cfg, resolve=True)

        # logging parameters
        self.success = True
        self.current = "__initialize_config"
        self.failure_detected = False

        # get input file name
        self.input_file_name = None

        # sanity check status
        self.preprocessing_check = False 
        self.training_check = False 
        self.inference_check = False

    def __check_pipeline(func):
        """Logs in the information/failures at every stage in the pipeline."""

        def wrapper(self, *args, **kwargs):
            if self.success:
                try:
                    func(self, *args, **kwargs)
                except Exception as e:
                    self.success = False
                    self.current = func.__name__
                    logger.error(f"The following error occured in the '{func.__name__}' stage: \n {e}")

            else:
                    if not self.failure_detected:
                        self.failure_detected = True
                        logger.error(f"**** FAILED: Cbrain pipeline failed at '{self.current}', check logs for errors ****")
        return wrapper

    def __preprocessing_sanity_check(self):

        logger.info("preprocess sanity check started")
        #check preprocess_config key
        if "preprocess_config" not in self.cfg or not self.cfg["preprocess_config"]:
            raise KeyError("preprocess_config key required")

        if "mode" not in self.cfg or not self.cfg["mode"]:
            raise KeyError("mode key required for preprocess")

        if "running_mode" not in self.cfg or not self.cfg["running_mode"]:
             raise KeyError("running_mode key required for preprocess")


        # check keys accessed inside preprocess_config
        keys_to_check = ['input', 'output', 'pointcloud_transformation', 'subtile'] 
        missing_or_none_keys = [key for key in keys_to_check if key not in self.cfg["preprocess_config"] or self.cfg["preprocess_config"][key] is None]

        if missing_or_none_keys:
                    raise ValueError(f"{missing_or_none_keys} keys required in preprocess_config")

        # check keys accessed inside preprocess_config.subtile
        subtile_keys_to_check = ['pdal_tile_length', 'pdal_tile_points', 'pdal_tile_buffer'] 
        subtile_missing_or_none_keys = [key for key in subtile_keys_to_check if key not in self.cfg["preprocess_config"]["subtile"] or self.cfg["preprocess_config"]["subtile"][key] is None]

        if subtile_missing_or_none_keys:
                    raise ValueError(f"{subtile_missing_or_none_keys} keys required in preprocess_config.subtile and cannot be None")

        # check existence of keys accesed during preprocess
        try:
            self.cfg["mode"]['datamodule']
        except:
                raise KeyError("datamodule key needed")

        try:
             self.cfg["preprocess_config"]["input"]["infile_path"]
        except:
             raise ValueError("Input laz file needed for preprocessing")

        self.preprocessing_check = True
        logger.info("preprocess sanity check successful")

    def __training_sanity_check(self):

            logger.info("training sanity check started")
            # check if mode is set in the default config and is not none
            if "mode" not in self.cfg or not self.cfg["mode"]:
                raise KeyError("mode key is required and cannot be None")

            if self.cfg["running_mode"] == "inference" :
                raise ValueError("training cannot be invoked in inference mode")

            # check if major keys required for training are present
            training_keys = ['run_inference', 'model', 'datamodule', 'callbacks', 'trainer', 'optimizer', 'losses', 'metrics'] 
            missing_or_none_keys = [key for key in training_keys if key not in self.cfg["mode"] or self.cfg["mode"][key] is None]

            if missing_or_none_keys:
                raise ValueError(f"{missing_or_none_keys} keys required and cannot be None")


            # check existence of keys accesed during training
            try:
                self.cfg["mode"]["callbacks"]["model_checkpoint"]
            except:
                raise KeyError("callbacks require model_checkpoint key")

            try:
                 self.cfg["mode"]["trainer"]["logger"]
            except:
                 raise KeyError("trainer requires logger key")
            self.training_check = True
            logger.info("training sanity check successful")

    def __inference_sanity_check(self):

            logger.info("inference sanity check started")
            # check if mode is set in the default config and is not none
            if "mode" not in self.cfg or not self.cfg["mode"]:
                raise KeyError("mode key is required and cannot be None")

            if self.cfg["running_mode"] == "training" :
                raise ValueError("inference cannot be invoked in training mode")

            # check if major keys required for inference are present
            inference_keys = ['checkpoint_path', 'datamodule', 'model', 'callbacks'] 
            missing_or_none_keys = [key for key in inference_keys if key not in self.cfg["mode"] or self.cfg["mode"][key] is None]
            if missing_or_none_keys:
                raise KeyError(f"{missing_or_none_keys} keys required and cannot be None")


            # check existence of keys accesed during inference
            try:
                 self.cfg["mode"]["callbacks"]["tile_inference"]
            except:
                 raise KeyError("callbacks require tile_inference key")
            self.inference_check = True

            logger.info("inference sanity check successful")

    def __postprocess_sanity_check(self):

        logger.info("postprocess sanity check started")
        keys_to_check = ['input', 'pointcloud_transformation', 'vegetation_classification', 'write_metadata'] 
        missing_or_none_keys = [key for key in keys_to_check if key not in self.cfg["postprocess_config"]]

        if missing_or_none_keys:
                    raise ValueError(f"{missing_or_none_keys} keys required in postprocess_config")

        try:
            self.cfg["postprocess_config"]['pointcloud_transformation']["ai_pc"]
        except:
                raise KeyError("Post process pointcloud_transformation requires ai_pc key")

        try:
            self.cfg["postprocess_config"]['pointcloud_transformation']["raw_pc"]
        except:
                raise KeyError("Postprocess pointcloud_transformation requires raw_pc key")

        if not self.cfg["postprocess_config"]["input"]["raw_pc"]:
             raise ValueError("Path to raw point cloud cannot be None")


        logger.info("postprocess sanity check successful")

    @__check_pipeline
    def start_preprocess(self):
        """
        Initiates preprocessing step of the C-brain.
        Runs is two modes: training and inference
        """
        # Verify if sanity checks have been performed
        if self.preprocessing_check:
             pass
        else:
            # sanity checks called when invoked as standalone preprocess
            self.__preprocessing_sanity_check()

        # Create preprocess_output directory
        self.subtile_path = os.path.join(self.output_dir, "preprocess_output")
        os.makedirs(self.subtile_path)

        # Update output path in preprocess_config
        self.cfg["preprocess_config"]["output"]["outfile_path"] = self.subtile_path

        # set path
        if self.cfg["running_mode"] == "inference":
            self.cfg["mode"]['datamodule']["predict_data_dir"] = str(self.subtile_path)
        elif self.cfg["running_mode"] == "training":
            self.cfg["mode"]["datamodule"]["data_dir"] = str(self.subtile_path)

        # Start preprocess
        preprocessor= Preprocessor(config = self.cfg["preprocess_config"], mode = self.cfg["running_mode"])
        preprocessor.start_preprocess()
        logger.info(f"Pre process files generated saved in the folder {self.subtile_path}")

    @__check_pipeline  
    def start_inference(self):
        """Initiates inference step of C-brain"""
        # sanity checks
        if self.inference_check:
             pass
        else:
            self.__inference_sanity_check()

            # check if input directory exists when invoked as standalone process
            if not self.cfg.mode['datamodule']["predict_data_dir"]:
                 raise ValueError("Directory to input laz files required for standalone preprocess")

        # Create predictions directory to store the output of inference and callback
        predictions_path = os.path.join(self.output_dir, "predictions")
        os.makedirs(predictions_path) 

        # Set the callbacks output directory
        self.cfg["mode"]["callbacks"]["tile_inference"]["output_dir"] = predictions_path

        # Start inference
        inference(self.cfg["mode"])
        logger.info(f"Inference files generated saved in the folder {predictions_path}")

    @__check_pipeline
    def start_training(self):
        """ Invokes training pipeline"""
        # sanity checks
        if self.training_check:
             pass
        else:
            self.__training_sanity_check()

             # check if input directory exists when invoked as standalone process
            if not self.cfg["mode"]['datamodule']["data_dir"]:
                 raise ValueError("Directory to input laz files required for standalone training process")

        self.cfg["mode"]["callbacks"]["model_checkpoint"]["dirpath"] = os.path.join(self.output_dir , "checkpoints")
        os.mkdir(os.path.join(self.output_dir , "wandb"))
        self.cfg["mode"]["trainer"]["logger"]["save_dir"] = os.path.join(self.output_dir , "wandb")
        train(self.cfg["mode"])
        logger.info(f"files generated saved in the folder {self.output_dir}")

    @__check_pipeline
    def __start_postprocess(self):
        """Invokes postprocess step of C-brain"""

        # Extract the file generated after inference step
        callback_path = os.path.join(self.output_dir , "predictions")
        items = os.listdir(callback_path)
        files = [f for f in items if os.path.isfile(os.path.join(callback_path, f))]
        ai_pc_path = os.path.join(callback_path , files[0])


        # Create temp and final_output directories
        os.mkdir(os.path.join(self.output_dir, "temp"))
        os.mkdir(os.path.join(self.output_dir, "final_output"))

        # get input file name
        file_path = Path(self.cfg["postprocess_config"]["input"]["raw_pc"])
        file_name = file_path.stem

        # Update paths in cfg
        self.cfg["postprocess_config"]["input"]["ai_pc"] = str(ai_pc_path)
        self.cfg["postprocess_config"]["temp"] = os.path.join(self.output_dir, "final_output/final.laz")
        self.cfg["postprocess_config"]["output"] = os.path.join(self.output_dir , f"temp/{file_name}_classified.laz")

        # Start post-process
        postprocecessor = Postprocessor(config= self.cfg["postprocess_config"])
        postprocecessor.start_postprocess()

    @__check_pipeline
    def run_cbrain_inference(self):
         """ Run C-brain pipeline"""
         self.__preprocessing_sanity_check()
         self.__inference_sanity_check()
         self.__postprocess_sanity_check()
         self.start_preprocess()
         self.start_inference()
         self.__start_postprocess()
         logger.info(f"files generated saved in the folder {self.output_dir}")

    @__check_pipeline
    def run_cbrain_training(self):
        """ Run C-brain training pipeline"""
        self.__preprocessing_sanity_check()
        self.__training_sanity_check()
        self.start_preprocess()
        self.start_training()
        logger.info(f"files generated saved in the folder {self.output_dir}")

