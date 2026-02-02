"""
Training Data Generator for Hail ML Model

Generates synthetic training data for development and testing.
In production, this should be supplemented with real NWS storm reports
matched to radar observations.

SWATH UPGRADE 5 - PART 12: Machine Learning Model
"""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import numpy as np

from .hail_ml_model import HailFeatures, TrainingExample


@dataclass
class SyntheticStormConfig:
    """Configuration for synthetic storm generation."""

    # Hail probability in dataset
    hail_probability: float = 0.4

    # Size distribution parameters
    hail_size_mean: float = 3.0  # Log-normal mean
    hail_size_std: float = 0.5   # Log-normal std
    min_hail_size_mm: float = 12.0
    max_hail_size_mm: float = 120.0

    # Reflectivity parameters
    base_reflectivity_hail: float = 55.0
    reflectivity_per_size: float = 0.2  # dBZ per mm
    reflectivity_noise: float = 3.0

    # Environmental parameters
    cape_mean: float = 1800.0
    cape_std: float = 600.0
    freezing_level_mean: float = 3.5
    freezing_level_std: float = 0.5

    # Location bounds (Tornado Alley)
    lat_range: Tuple[float, float] = (30.0, 40.0)
    lon_range: Tuple[float, float] = (-102.0, -94.0)


class TrainingDataGenerator:
    """
    Generate synthetic training data for hail ML model.

    Produces realistic radar and environmental observations
    with known ground truth for model training.

    Example:
        >>> generator = TrainingDataGenerator()
        >>> training_data = generator.generate(n_samples=3000)
        >>> hail_count = sum(1 for ex in training_data if ex.hail_occurred)
        >>> print(f"Generated {len(training_data)} samples, {hail_count} hail cases")
    """

    def __init__(
        self,
        config: Optional[SyntheticStormConfig] = None,
        random_seed: int = 42
    ):
        """
        Initialize the generator.

        Args:
            config: Storm generation configuration
            random_seed: Random seed for reproducibility
        """
        self.config = config or SyntheticStormConfig()
        np.random.seed(random_seed)

    def generate(
        self,
        n_samples: int = 3000,
        start_time: Optional[datetime] = None,
        include_marginal: bool = True
    ) -> List[TrainingExample]:
        """
        Generate training dataset.

        Args:
            n_samples: Number of samples to generate
            start_time: Base time for samples
            include_marginal: Include marginal/borderline cases

        Returns:
            List of TrainingExample objects
        """
        if start_time is None:
            start_time = datetime(2024, 5, 15, 14, 0)  # Peak hail season

        examples = []

        for i in range(n_samples):
            # Determine if hail case
            is_hail = np.random.random() < self.config.hail_probability

            if is_hail:
                example = self._generate_hail_case(i, start_time)
            else:
                example = self._generate_non_hail_case(i, start_time)

            examples.append(example)

        # Add marginal cases for better model boundary learning
        if include_marginal:
            n_marginal = n_samples // 10
            marginal_cases = self._generate_marginal_cases(
                n_marginal, len(examples), start_time
            )
            examples.extend(marginal_cases)

        return examples

    def _generate_hail_case(
        self,
        index: int,
        base_time: datetime
    ) -> TrainingExample:
        """Generate a hail storm example."""

        # Hail size from log-normal distribution
        hail_size = np.random.lognormal(
            self.config.hail_size_mean,
            self.config.hail_size_std
        )
        hail_size = min(
            max(hail_size, self.config.min_hail_size_mm),
            self.config.max_hail_size_mm
        )

        # Reflectivity correlates with size
        max_refl = (
            self.config.base_reflectivity_hail +
            (hail_size / 120) * 20 +
            np.random.normal(0, self.config.reflectivity_noise)
        )
        max_refl = min(max_refl, 75)

        # MESH correlates with actual size (with measurement error)
        mesh = hail_size * (1 + np.random.normal(0, 0.15))
        mesh = max(mesh, 10)

        # POSH increases with size
        posh = min(99, 30 + (hail_size / 50) * 60 + np.random.normal(0, 5))

        # Lower ZDR for hail (tumbling stones)
        zdr_min = 0.5 - (hail_size / 100) * 1.0 + np.random.normal(0, 0.2)
        zdr_mean = zdr_min + np.random.uniform(0.3, 0.7)

        # Lower CC for hail (mixed phase, irregular shapes)
        cc_min = 0.97 - (hail_size / 100) * 0.05 + np.random.normal(0, 0.01)
        cc_min = max(cc_min, 0.85)
        cc_mean = cc_min + np.random.uniform(0.01, 0.03)

        # Higher VIL for hail
        vil = 30 + (hail_size / 50) * 40 + np.random.normal(0, 5)

        # Higher KDP indicates more liquid water
        kdp_max = np.random.uniform(1.0, 4.0)

        # CAPE typically higher for hail
        cape = self.config.cape_mean + np.random.normal(0, self.config.cape_std)
        cape = max(cape, 500)

        # Freezing level
        freezing = (
            self.config.freezing_level_mean +
            np.random.normal(0, self.config.freezing_level_std)
        )

        # Shear and SRH
        shear = np.random.uniform(20, 45)
        srh = np.random.uniform(150, 350)

        # Storm structure
        storm_top = np.random.uniform(10, 16)
        mean_refl = max_refl - np.random.uniform(10, 18)
        gradient = max_refl - mean_refl

        # Cell characteristics
        cell_area = np.random.uniform(40, 200)
        cell_velocity = np.random.uniform(35, 75)
        cell_duration = np.random.uniform(20, 90)
        stage = np.random.choice(
            ['intensifying', 'mature', 'weakening'],
            p=[0.3, 0.5, 0.2]
        )

        features = HailFeatures(
            max_reflectivity=max_refl,
            mean_reflectivity=mean_refl,
            reflectivity_gradient=gradient,
            vil=vil,
            mesh=mesh,
            posh=posh,
            zdr_min=zdr_min,
            zdr_mean=zdr_mean,
            cc_min=cc_min,
            cc_mean=cc_mean,
            kdp_max=kdp_max,
            storm_top_height=storm_top,
            freezing_level=freezing,
            cape=cape,
            shear_0_6km=shear,
            storm_relative_helicity=srh,
            cell_area_km2=cell_area,
            cell_velocity_kmh=cell_velocity,
            cell_duration_minutes=cell_duration,
            lifecycle_stage=stage
        )

        lat = np.random.uniform(*self.config.lat_range)
        lon = np.random.uniform(*self.config.lon_range)

        return TrainingExample(
            features=features,
            hail_occurred=True,
            hail_size_mm=hail_size,
            event_time=base_time + timedelta(minutes=index * 5),
            location=(lat, lon),
            source='simulation'
        )

    def _generate_non_hail_case(
        self,
        index: int,
        base_time: datetime
    ) -> TrainingExample:
        """Generate a non-hail storm example."""

        # Lower reflectivity
        max_refl = np.random.uniform(35, 55)
        mean_refl = max_refl - np.random.uniform(8, 15)
        gradient = max_refl - mean_refl

        # Low or no MESH/POSH
        mesh = np.random.uniform(0, 15)
        posh = np.random.uniform(0, 25)

        # Higher ZDR (rain drops are oblate)
        zdr_min = np.random.uniform(0.8, 2.5)
        zdr_mean = zdr_min + np.random.uniform(0.2, 0.5)

        # Higher CC (uniform rain)
        cc_min = np.random.uniform(0.96, 0.995)
        cc_mean = cc_min + np.random.uniform(0.002, 0.005)

        # Lower VIL
        vil = np.random.uniform(5, 30)

        # KDP
        kdp_max = np.random.uniform(0.5, 3.5)

        # Lower CAPE typical for non-hail
        cape = np.random.uniform(500, 1500)

        # Environmental
        freezing = np.random.uniform(3.0, 4.5)
        shear = np.random.uniform(10, 30)
        srh = np.random.uniform(50, 200)

        # Storm structure
        storm_top = np.random.uniform(6, 12)

        # Cell characteristics
        cell_area = np.random.uniform(15, 100)
        cell_velocity = np.random.uniform(25, 60)
        cell_duration = np.random.uniform(10, 60)
        stage = np.random.choice(
            ['initiation', 'mature', 'weakening', 'dissipating']
        )

        features = HailFeatures(
            max_reflectivity=max_refl,
            mean_reflectivity=mean_refl,
            reflectivity_gradient=gradient,
            vil=vil,
            mesh=mesh,
            posh=posh,
            zdr_min=zdr_min,
            zdr_mean=zdr_mean,
            cc_min=cc_min,
            cc_mean=cc_mean,
            kdp_max=kdp_max,
            storm_top_height=storm_top,
            freezing_level=freezing,
            cape=cape,
            shear_0_6km=shear,
            storm_relative_helicity=srh,
            cell_area_km2=cell_area,
            cell_velocity_kmh=cell_velocity,
            cell_duration_minutes=cell_duration,
            lifecycle_stage=stage
        )

        lat = np.random.uniform(*self.config.lat_range)
        lon = np.random.uniform(*self.config.lon_range)

        return TrainingExample(
            features=features,
            hail_occurred=False,
            hail_size_mm=0,
            event_time=base_time + timedelta(minutes=index * 5),
            location=(lat, lon),
            source='simulation'
        )

    def _generate_marginal_cases(
        self,
        n_samples: int,
        start_index: int,
        base_time: datetime
    ) -> List[TrainingExample]:
        """
        Generate borderline cases near the decision boundary.

        These help the model learn nuanced differences between
        hail and non-hail cases.
        """
        examples = []

        for i in range(n_samples):
            # 50/50 hail/non-hail for marginal cases
            is_hail = np.random.random() < 0.5

            # Marginal reflectivity (50-58 dBZ)
            max_refl = np.random.uniform(50, 58)
            mean_refl = max_refl - np.random.uniform(8, 12)

            if is_hail:
                # Small hail
                hail_size = np.random.uniform(12, 25)
                mesh = hail_size * np.random.uniform(0.85, 1.15)
                posh = np.random.uniform(25, 50)
                zdr_min = np.random.uniform(0.3, 0.8)
                cc_min = np.random.uniform(0.93, 0.96)
                vil = np.random.uniform(25, 40)
            else:
                hail_size = 0
                mesh = np.random.uniform(5, 20)
                posh = np.random.uniform(15, 40)
                zdr_min = np.random.uniform(0.6, 1.2)
                cc_min = np.random.uniform(0.95, 0.98)
                vil = np.random.uniform(15, 35)

            # Common marginal parameters
            zdr_mean = zdr_min + np.random.uniform(0.2, 0.4)
            cc_mean = cc_min + np.random.uniform(0.01, 0.02)
            kdp_max = np.random.uniform(1.0, 3.0)
            cape = np.random.uniform(1000, 2000)
            freezing = np.random.uniform(3.2, 3.8)
            shear = np.random.uniform(18, 32)
            srh = np.random.uniform(120, 220)
            storm_top = np.random.uniform(9, 12)
            gradient = max_refl - mean_refl

            cell_area = np.random.uniform(30, 100)
            cell_velocity = np.random.uniform(35, 55)
            cell_duration = np.random.uniform(15, 45)
            stage = np.random.choice(['intensifying', 'mature', 'weakening'])

            features = HailFeatures(
                max_reflectivity=max_refl,
                mean_reflectivity=mean_refl,
                reflectivity_gradient=gradient,
                vil=vil,
                mesh=mesh,
                posh=posh,
                zdr_min=zdr_min,
                zdr_mean=zdr_mean,
                cc_min=cc_min,
                cc_mean=cc_mean,
                kdp_max=kdp_max,
                storm_top_height=storm_top,
                freezing_level=freezing,
                cape=cape,
                shear_0_6km=shear,
                storm_relative_helicity=srh,
                cell_area_km2=cell_area,
                cell_velocity_kmh=cell_velocity,
                cell_duration_minutes=cell_duration,
                lifecycle_stage=stage
            )

            lat = np.random.uniform(*self.config.lat_range)
            lon = np.random.uniform(*self.config.lon_range)

            example = TrainingExample(
                features=features,
                hail_occurred=is_hail,
                hail_size_mm=hail_size,
                event_time=base_time + timedelta(minutes=(start_index + i) * 5),
                location=(lat, lon),
                source='simulation_marginal'
            )

            examples.append(example)

        return examples

    def generate_balanced_dataset(
        self,
        n_hail: int = 1500,
        n_non_hail: int = 1500,
        start_time: Optional[datetime] = None
    ) -> List[TrainingExample]:
        """
        Generate a balanced dataset with equal hail/non-hail.

        Args:
            n_hail: Number of hail cases
            n_non_hail: Number of non-hail cases
            start_time: Base time

        Returns:
            Balanced list of TrainingExample objects
        """
        if start_time is None:
            start_time = datetime(2024, 5, 15, 14, 0)

        examples = []

        # Hail cases
        for i in range(n_hail):
            examples.append(self._generate_hail_case(i, start_time))

        # Non-hail cases
        for i in range(n_non_hail):
            examples.append(
                self._generate_non_hail_case(n_hail + i, start_time)
            )

        # Shuffle
        np.random.shuffle(examples)

        return examples

    def generate_size_stratified(
        self,
        n_samples_per_bin: int = 200
    ) -> List[TrainingExample]:
        """
        Generate dataset stratified by hail size.

        Ensures good representation of all size categories.

        Size bins:
        - No hail: 0 mm
        - Small: 12-25 mm
        - Medium: 25-45 mm
        - Large: 45-65 mm
        - Giant: 65+ mm
        """
        examples = []
        base_time = datetime(2024, 5, 15, 14, 0)

        size_bins = [
            (0, 0, 0),           # No hail
            (12, 25, 1),         # Small
            (25, 45, 2),         # Medium
            (45, 65, 3),         # Large
            (65, 120, 4)         # Giant
        ]

        for min_size, max_size, bin_idx in size_bins:
            for i in range(n_samples_per_bin):
                idx = bin_idx * n_samples_per_bin + i

                if min_size == 0:
                    # Non-hail case
                    example = self._generate_non_hail_case(idx, base_time)
                else:
                    # Force specific size range
                    example = self._generate_hail_case(idx, base_time)
                    # Adjust to be within bin
                    example.hail_size_mm = np.random.uniform(min_size, max_size)
                    example.features.mesh = example.hail_size_mm * np.random.uniform(0.9, 1.1)

                examples.append(example)

        np.random.shuffle(examples)
        return examples

    def get_dataset_stats(
        self,
        examples: List[TrainingExample]
    ) -> Dict:
        """
        Get statistics about a training dataset.

        Args:
            examples: Training examples

        Returns:
            Dict with dataset statistics
        """
        hail_cases = [ex for ex in examples if ex.hail_occurred]
        non_hail_cases = [ex for ex in examples if not ex.hail_occurred]

        hail_sizes = [ex.hail_size_mm for ex in hail_cases]
        reflectivities = [ex.features.max_reflectivity for ex in examples]
        mesh_values = [ex.features.mesh for ex in examples]

        return {
            'total_samples': len(examples),
            'hail_samples': len(hail_cases),
            'non_hail_samples': len(non_hail_cases),
            'hail_ratio': len(hail_cases) / len(examples),
            'hail_size_stats': {
                'mean': np.mean(hail_sizes) if hail_sizes else 0,
                'std': np.std(hail_sizes) if hail_sizes else 0,
                'min': min(hail_sizes) if hail_sizes else 0,
                'max': max(hail_sizes) if hail_sizes else 0
            },
            'reflectivity_stats': {
                'mean': np.mean(reflectivities),
                'std': np.std(reflectivities),
                'min': min(reflectivities),
                'max': max(reflectivities)
            },
            'mesh_stats': {
                'mean': np.mean(mesh_values),
                'std': np.std(mesh_values),
                'min': min(mesh_values),
                'max': max(mesh_values)
            },
            'sources': list(set(ex.source for ex in examples))
        }


# ============================================================================
# Test
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("TRAINING DATA GENERATOR TEST")
    print("=" * 70)

    generator = TrainingDataGenerator()

    print("\n[1/4] Generating standard dataset...")
    standard_data = generator.generate(n_samples=1000)
    stats = generator.get_dataset_stats(standard_data)

    print(f"  Total samples: {stats['total_samples']}")
    print(f"  Hail samples: {stats['hail_samples']} ({stats['hail_ratio']*100:.1f}%)")
    print(f"  Mean hail size: {stats['hail_size_stats']['mean']:.1f} mm")
    print(f"  Mean reflectivity: {stats['reflectivity_stats']['mean']:.1f} dBZ")

    print("\n[2/4] Generating balanced dataset...")
    balanced_data = generator.generate_balanced_dataset(n_hail=500, n_non_hail=500)
    balanced_stats = generator.get_dataset_stats(balanced_data)
    print(f"  Total: {balanced_stats['total_samples']}")
    print(f"  Hail ratio: {balanced_stats['hail_ratio']*100:.1f}%")

    print("\n[3/4] Generating size-stratified dataset...")
    stratified_data = generator.generate_size_stratified(n_samples_per_bin=100)
    strat_stats = generator.get_dataset_stats(stratified_data)
    print(f"  Total: {strat_stats['total_samples']}")
    print(f"  Size range: {strat_stats['hail_size_stats']['min']:.1f} - {strat_stats['hail_size_stats']['max']:.1f} mm")

    print("\n[4/4] Size distribution in stratified dataset:")
    size_bins = {'none': 0, 'small': 0, 'medium': 0, 'large': 0, 'giant': 0}
    for ex in stratified_data:
        if not ex.hail_occurred:
            size_bins['none'] += 1
        elif ex.hail_size_mm < 25:
            size_bins['small'] += 1
        elif ex.hail_size_mm < 45:
            size_bins['medium'] += 1
        elif ex.hail_size_mm < 65:
            size_bins['large'] += 1
        else:
            size_bins['giant'] += 1

    for bin_name, count in size_bins.items():
        print(f"  {bin_name}: {count}")

    print("\n" + "=" * 70)
    print("DATA GENERATION COMPLETE")
    print("=" * 70)
