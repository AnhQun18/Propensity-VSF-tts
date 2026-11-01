from setuptools import setup, find_packages

setup(
    name="propensity_model",
    version="0.1.0",
    author="Propensity Modeling Team",
    description="End-to-End Propensity Modeling Pipeline for Customer Conversion & Retention",
    long_description=open("README.md", encoding="utf-8").read() if open("README.md", encoding="utf-8") else "",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scipy>=1.10.0",
        "scikit-learn>=1.3.0",
        "lightgbm>=4.0.0",
        "xgboost>=2.0.0",
        "catboost>=1.2.0",
        "pyyaml>=6.0.0",
        "pyarrow>=14.0.0",
        "joblib>=1.3.0",
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "optuna>=3.3.0",
            "jupyter>=1.0.0",
            "ipykernel>=6.25.0",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
