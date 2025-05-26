from setuptools import setup, find_packages

setup(
    name="nga",  # 包的名称
    version="0.1.0",    # 包的版本
    packages=find_packages(),  # 自动发现源代码包
    install_requires=[  # 外部依赖包
        # "numpy",  # 示例依赖
        # "pandas",  # 示例依赖
    ],
    include_package_data=True,  # 包含非 Python 文件
    description="A package for dify code block nga functions",  # 包的描述
    long_description=open("README.md").read(),  # 从 README 文件中读取更详细的描述
    long_description_content_type="text/markdown",  # 描述文件的格式
    author="Hong",  # 作者名
    author_email="hong.zheng@newbakery.net",  # 作者电子邮件
    url="",  # 项目链接
    classifiers=[  # 选择合适的分类
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",  # Python 最低版本要求
)