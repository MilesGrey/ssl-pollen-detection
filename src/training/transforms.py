"""Adapted from https://github.com/pytorch/vision/tree/main/references/detection"""
import random

import torch
from torch import Tensor
from torchvision.transforms import functional as F


def _flip_coco_person_keypoints(kps, width):
    flip_inds = [0, 2, 1, 4, 3, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16, 15]
    flipped_data = kps[:, flip_inds]
    flipped_data[..., 0] = width - flipped_data[..., 0]
    # Maintain COCO convention that if visibility == 0, then x, y = 0
    inds = flipped_data[..., 2] == 0
    flipped_data[inds] = 0
    return flipped_data


class Compose(object):
    def __init__(self, transforms):
        self.transforms = transforms

    def __call__(self, image, target):
        for t in self.transforms:
            image, target = t(image, target)
        return image, target


class RandomHorizontalFlip(object):
    def __init__(self, prob):
        self.prob = prob

    def __call__(self, image, target):
        if random.random() < self.prob:
            height, width = image.shape[-2:]
            image = image.flip(-1)
            bbox = target["boxes"]
            bbox[:, [0, 2]] = width - bbox[:, [2, 0]]
            target["boxes"] = bbox
        return image, target


class RandomVerticalFlip(object):
    def __init__(self, prob):
        self.prob = prob

    def __call__(self, image, target):
        if random.random() < self.prob:
            height, width = image.shape[-2:]
            image = image.flip(-2)
            bbox = target["boxes"]
            bbox[:, [1, 3]] = height - bbox[:, [3, 1]]
            target["boxes"] = bbox
        return image, target


class ToTensor(object):
    def __call__(self, image, target):
        image = F.to_tensor(image)
        return image, target


class RandomRotation(object):
    def __init__(self, prob, degree_range, image_size):
        self.prob = prob
        self.degree_range = degree_range
        self.image_size = image_size

    def __call__(self, image, target):
        if random.random() < self.prob:
            degree = float(torch.rand(1)) * 2 * self.degree_range - self.degree_range
            image = F.rotate(image, angle=degree)
            target['boxes'] = self._rotate_coordinates(
                box_coordinates=target['boxes'],
                x_center=self.image_size[0] / 2,
                y_center=self.image_size[1] / 2,
                degree=degree
            )
        return image, target

    @staticmethod
    def _rotate_coordinates(
            box_coordinates: Tensor,
            x_center: float,
            y_center: float,
            degree: float
    ):
        """
        Rotates bounding box coordinates around the center.

        Rotates the original bounding box and encloses the resulting box with a new box that is parallel to the image
        border.

        Args:
            box_coordinates: Coordinates of the form [[x1, y1, x2, y3], ...] where (x1, y1) denotes the upper left
                corner and (x2, y2) denotes the lower right corner of the bounding box.
            x_center: Center coordinate of the x-axis.
            y_center: Center coordinate of the y-axis.
            degree: Degree for which to rotate the coordinates counter-clockwise.

        Returns:

        """
        # Make rotation counter-clockwise
        degree = torch.tensor(-degree)

        radians = degree * torch.pi / 180

        x_minus_center = box_coordinates[:, [0, 2, 2, 0]] - x_center
        y_minus_center = box_coordinates[:, [1, 3, 1, 3]] - y_center

        x_rotated = x_minus_center * torch.cos(radians) - y_minus_center * torch.sin(radians) + x_center
        y_rotated = x_minus_center * torch.sin(radians) + y_minus_center * torch.cos(radians) + y_center

        box_coordinates[:, 0] = torch.min(x_rotated, dim=-1)[0]
        box_coordinates[:, 2] = torch.max(x_rotated, dim=-1)[0]
        box_coordinates[:, 1] = torch.min(y_rotated, dim=-1)[0]
        box_coordinates[:, 3] = torch.max(y_rotated, dim=-1)[0]

        return box_coordinates
