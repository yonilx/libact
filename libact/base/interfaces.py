"""
Base interfaces for use in the package.
The package works according to the interfaces defined below.
"""
import numpy as np
from libact.utils import seed_random_state
from six import with_metaclass

from abc import ABCMeta, abstractmethod


class QueryStrategy(with_metaclass(ABCMeta, object)):

    """Pool-based query strategy

    A QueryStrategy advices on which unlabeled data to be queried next given
    a pool of labeled and unlabeled data.
    """

    def __init__(self, dataset, **kwargs):
        self._dataset = dataset
        self.scores_dict = None
        self.real_scores_dict = None
        self.scores_valid = False
        dataset.on_update(self.update)
        self.random_state_ = seed_random_state(5)  # default random state

    @property
    def dataset(self):
        """The Dataset object that is associated with this QueryStrategy."""
        return self._dataset

    @staticmethod
    def _port_dict_to_0_1_range(scores_dict):
        min_val, max_val = min(scores_dict.itervalues()), max(scores_dict.itervalues())
        # change range to be between 0,1
        return dict(map(lambda t: (t[0], np.interp(t[1],[min_val, max_val], [0, 1])), scores_dict.iteritems()))

    def update_scores_list(self):
        """updates self.scores_list and self.unlabeled_entry_ids if needed """
        if (self.scores_dict is None or self.real_scores_dict is None) or not self.scores_valid:
            self.real_scores_dict = self.retrieve_score_list()
            self.scores_dict = self._port_dict_to_0_1_range(self.real_scores_dict)
            self.scores_valid = True

    def update(self, entry_id, label):
        """Update the internal states of the QueryStrategy after each queried
        sample being labeled.
        If retrieve_score_list() is implemented, when overriding update() the super method must be called

        Parameters
        ----------
        entry_id : int
            The index of the newly labeled sample.

        label : float
            The label of the queried sample.
        """
        self.scores_valid = False

    def make_query(self, return_score=False):
        """Return the index of the sample to be queried and labeled. Read-only.
        Chooses the lowest score unlabeled example
        No modification to the internal states.

        Returns
        -------
        ask_id : int
            The index of the next unlabeled sample to be queried and labeled.
        """
        self.update_scores_list()
        # shuffle order for randomality
        combined = list(self.scores_dict.iteritems())
        # self.random_state_.shuffle(combined)
        unlabeled_entry_ids, score_list = zip(*combined)
        ask_id = unlabeled_entry_ids[np.argmax(score_list)]
        if not return_score:
            return ask_id
        else:
            return ask_id, combined

    def retrieve_score_list(self):
        """Returns a score list for all unlabeled instances in the dataset
        and in addition returns a list which maps indexes in the score list to the indexes in the dataset

        Returns
        -------
        score_list : list
            Active learning score for each unlabeled instance in the dataset
        unlabeled_entry_ids : list
            Maps indexes in the score list to the indexes in the dataset"""
        raise NotImplementedError  # must be implemented if planned to be used (but not always used)

    def get_score(self, entry_id):
        """Return the the score given to a requested sample from the dataset. Read-only.

        No modification to the internal states.

        Parameters
        ----------
        entry_id : int
            The index of our requested sample.

        Returns
        -------
        score : float
            The given to the sample by the query strategy, the larger the better
        """
        self.update_scores_list()
        return self.scores_dict[entry_id]


class Labeler(with_metaclass(ABCMeta, object)):

    """Label the queries made by QueryStrategies

    Assign labels to the samples queried by QueryStrategies.
    """
    @abstractmethod
    def label(self, feature):
        """Return the class labels for the input feature array.

        Parameters
        ----------
        feature : array-like, shape (n_features,)
            The feature vector whose label is to queried.

        Returns
        -------
        label : int
            The class label of the queried feature.
        """
        pass


class Model(with_metaclass(ABCMeta, object)):

    """Classification Model

    A Model returns a class-predicting function for future samples after
    trained on a training dataset.
    """
    @abstractmethod
    def train(self, dataset, *args, **kwargs):
        """Train a model according to the given training dataset.

        Parameters
        ----------
        dataset : Dataset object
             The training dataset the model is to be trained on.

        Returns
        -------
        self : object
            Returns self.
        """
        pass

    @abstractmethod
    def predict(self, feature, *args, **kwargs):
        """Predict the class labels for the input samples

        Parameters
        ----------
        feature : array-like, shape (n_samples, n_features)
            The unlabeled samples whose labels are to be predicted.

        Returns
        -------
        y_pred : array-like, shape (n_samples,)
            The class labels for samples in the feature array.
        """
        pass

    @abstractmethod
    def score(self, testing_dataset, *args, **kwargs):
        """Return the mean accuracy on the test dataset

        Parameters
        ----------
        testing_dataset : Dataset object
            The testing dataset used to measure the perforance of the trained
            model.

        Returns
        -------
        score : float
            Mean accuracy of self.predict(X) wrt. y.
        """
        pass


class MultilabelModel(Model):
    """Multilabel Classification Model

    A Model returns a multilabel-predicting function for future samples after
    trained on a training dataset.
    """
    pass


class ContinuousModel(Model):

    """Classification Model with intermediate continuous output

    A continuous classification model is able to output a real-valued vector
    for each features provided.
    """
    @abstractmethod
    def predict_real(self, feature, *args, **kwargs):
        """Predict confidence scores for samples.

        Returns the confidence score for each (sample, class) combination.

        The larger the value for entry (sample=x, class=k) is, the more
        confident the model is about the sample x belonging to the class k.

        Take Logistic Regression as example, the return value is the signed
        distance of that sample to the hyperplane.

        Parameters
        ----------
        feature : array-like, shape (n_samples, n_features)
            The samples whose confidence scores are to be predicted.

        Returns
        -------
        X : array-like, shape (n_samples, n_classes)
            Each entry is the confidence scores per (sample, class)
            combination.
        """
        pass


class ProbabilisticModel(ContinuousModel):

    """Classification Model with probability output

    A probabilistic classification model is able to output a real-valued vector
    for each features provided.
    """
    def predict_real(self, feature, *args, **kwargs):
        return self.predict_proba(feature, *args, **kwargs)

    @abstractmethod
    def predict_proba(self, feature, *args, **kwargs):
        """Predict probability estimate for samples.

        Parameters
        ----------
        feature : array-like, shape (n_samples, n_features)
            The samples whose probability estimation are to be predicted.

        Returns
        -------
        X : array-like, shape (n_samples, n_classes)
            Each entry is the prabablity estimate for each class.
        """
        pass
