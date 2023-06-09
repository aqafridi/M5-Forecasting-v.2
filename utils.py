import numpy as np
from typing import Tuple
import modin.pandas as pd
import json

def get_xgboost_x_y(
    indices: list, 
    data: np.array,
    target_sequence_length,
    input_seq_len: int
    ) -> Tuple[np.array, np.array]:

    """
    Args:

        indices: List of index positions at which data should be sliced

        data: A univariate time series

        target_sequence_length: The forecasting horizon, m

        input_seq_len: The length of the model input, n

    Output: 

        all_x: np.array of shape (number of instances, input seq len)

        all_y: np.array of shape (number of instances, target seq len)

    """
    # print("Preparing data..")
    all_x =[]
    all_y =[]


    # Loop over list of training indices
    for i, idx in enumerate(indices):

        # Slice data into instance of length input length + target length
        data_instance = data[idx[0]:idx[1]]

        x = data_instance[0:input_seq_len]

        assert len(x) == input_seq_len

        y = data_instance[input_seq_len:input_seq_len+target_sequence_length]

        # Create all_y and all_x objects in first loop iteration
        if i == 0:

            all_y = y.reshape(1, -1)

            all_x = x.reshape(1, -1)

        else:

            all_y = np.concatenate((all_y, y.reshape(1, -1)), axis=0)

            all_x = np.concatenate((all_x, x.reshape(1, -1)), axis=0)

    # print("Finished preparing data!")

    return all_x, all_y


def get_indices_entire_sequence(
    data: pd.DataFrame, 
    window_size: int, 
    step_size: int
    ) -> list:
        """
        Produce all the start and end index positions that is needed to produce
        the sub-sequences. 
        Returns a list of tuples. Each tuple is (start_idx, end_idx) of a sub-
        sequence. These tuples should be used to slice the dataset into sub-
        sequences. These sub-sequences should then be passed into a function
        that slices them into input and target sequences. 
        
        Args:
            data (pd.DataFrame): Partitioned data set, e.g. training data

            window_size (int): The desired length of each sub-sequence. Should be
                               (input_sequence_length + target_sequence_length)
                               E.g. if you want the model to consider the past 100
                               time steps in order to predict the future 50 
                               time steps, window_size = 100+50 = 150
            step_size (int): Size of each step as the data sequence is traversed 
                             by the moving window.
                             If 1, the first sub-sequence will be [0:window_size], 
                             and the next will be [1:window_size].
        Return:
            indices: a list of tuples
        """

        stop_position = len(data)-1 # 1- because of 0 indexing
        
        # Start the first sub-sequence at index position 0
        subseq_first_idx = 0
        
        subseq_last_idx = window_size
        
        indices = []
        
        while subseq_last_idx <= stop_position:

            indices.append((subseq_first_idx, subseq_last_idx))
            
            subseq_first_idx += step_size
            
            subseq_last_idx += step_size

        return indices


def prepare_data_for_xgb(y_train_data_,y_test_data_,in_length,step_size,target_sequence_length):
    training_indices = get_indices_entire_sequence(
            data=y_train_data_, 
            window_size=in_length+target_sequence_length, 
            step_size=step_size
            )

        # Obtain (X,Y) pairs of training data
    x_train, y_train = get_xgboost_x_y(
        indices=training_indices, 
        data=y_train_data_.to_numpy(),
        target_sequence_length=target_sequence_length,
        input_seq_len=in_length
        )

    test_indices = get_indices_entire_sequence(
        data=y_test_data_, 
        window_size=in_length+target_sequence_length, 
        step_size=step_size
        )

    # Obtain (X,Y) pairs of test data
    x_test, y_test = get_xgboost_x_y(
        indices=test_indices, 
        data=y_test_data_.to_numpy(),
        target_sequence_length=target_sequence_length,
        input_seq_len=in_length
        )
    return x_train, y_train,x_test, y_test


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)

def save_to_json(filename, data, mode='w'):
    
    with open(f"./best_params/{filename}.json", mode) as f:
        json.dump(data, f,cls=NpEncoder)


def read_from_json(filename,mode="r"):
    with open(f'./best_params/{filename}.json', mode) as f:
        # Load the JSON data into a Python dictionary
        data = json.load(f)

        return data