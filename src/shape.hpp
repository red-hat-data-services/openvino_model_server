//*****************************************************************************
// Copyright 2021 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//*****************************************************************************
#pragma once

#include <string>
#include <unordered_map>
#include <vector>

#include <openvino/openvino.hpp>

#include "status.hpp"

namespace ovms {

using dimension_value_t = std::int64_t;

constexpr dimension_value_t DYNAMIC_DIMENSION = -1;

enum Mode { FIXED,
    AUTO };
using shape_t = std::vector<size_t>;

class Dimension {
    dimension_value_t minimum, maximum;

public:
    Dimension();

    Dimension(dimension_value_t dim);

    Dimension(dimension_value_t minimum, dimension_value_t maximum);

    bool isStatic() const;
    bool isDynamic() const;

    ov::Dimension createPartialDimension() const;

    // TODO: Remove. For OV API 1.0 compatibility purposes only.
    dimension_value_t getAnyValue() const;

    dimension_value_t getStaticValue() const;
    dimension_value_t getMinValue() const;
    dimension_value_t getMaxValue() const;

    bool operator==(const Dimension& rhs) const;
    bool operator!=(const Dimension& rhs) const;

    static Status fromString(const std::string& str, Dimension& dimOut);
    std::string toString() const;

    static Dimension any();
};

class Shape {
    std::vector<Dimension> dimensions;

public:
    Shape();

    // Create shape out of ovms::Shape{1, 5, 100, 100}
    Shape(std::initializer_list<Dimension> list);

    // Create ovms::Shape out of oridnary vector of dimensions.
    static Status fromFlatShape(const shape_t& shapeIn, Shape& shapeOut);

    // Create ovms::Shape out of ov::PartialShape.
    Shape(const ov::PartialShape& shape);

    Shape& add(const Dimension& dim);

    size_t getSize() const;

    bool isStatic() const;
    bool isDynamic() const;

    ov::PartialShape createPartialShape() const;

    // TODO: Remove. For OV API 1.0 compatibility purposes only.
    shape_t getFlatShape() const;

    bool operator==(const Shape& rhs) const;
    bool operator!=(const Shape& rhs) const;

    std::string toString() const;

    static Status fromString(const std::string& strIn, Shape& shapeOut);
};

using shapes_map_2_t = std::unordered_map<std::string, Shape>;

struct ShapeInfo_2 {
    Mode shapeMode = FIXED;
    Shape shape;

    operator std::string() const;

    bool operator==(const ShapeInfo_2& rhs) const {
        return this->shapeMode == rhs.shapeMode && this->shape == rhs.shape;
    }

    bool operator!=(const ShapeInfo_2& rhs) const {
        return !(*this == rhs);
    }
};

using shapes_info_map_2_t = std::unordered_map<std::string, ShapeInfo_2>;

}  // namespace ovms
